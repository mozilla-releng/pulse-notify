# Pulse-Notifier
Pulse-Notifier is used to take various actions based on the completion status of Taskcluster tasks, primarily notifications for failures and other important events. The program depends on the Taskcluster and Pulse tools at Mozilla.

### Technical Features
- Asynchronous Python 3.5
- Asynchronous AMQP consumer for Pulse messages
- Pluggable functionality/dependency injection.

## Core
Pulse-Notifier is an asynchronous event loop with an AMQP consumer listening for Taskcluster events on Mozilla Pulse. The consumer receives a message about the status of the task and parses the task definition for notification information. Based on the notification information, the consumer passes the necessary information to various channels of communication/action, called 'plugins'.

### Task Definition
To receive a notification from a task, the task definition must include an 'extra' section, with a 'notification' subsection. Within the notification section, each unique task status has it's notification configuration defined. Possible task statuses are:

- task-defined
- task-pending
- task-running
- artifact-created
- task-completed
- task-failed
- task-exception

Under each task status, the following fields can be defined:

- plugins: notification routes for this task status
- subject: notification subject
- message: notification message
- emails: emails to be notified (for ses and smtp plugins only)
- nicks: IRC nicknames to notify (for irc plugin only)
- channels: IRC channels to send a notification to (for irc plugin only)
- ids: notify a 'name' based on a configuration in the service

The fields subject and message are not required, a simple fallback message is enabled. Emails and nicks are also not necessary, the service will still try to notify regardless. Below is an example task definition:

    "extra": {
        "notifications": {
          "task-defined": {
            "message": "This task has been defined within TaskCluster",
            "subject": "task-defined notification",
            "plugins": [
              "ses"
            ],
            "emails": [
              "csheehan@mozilla.com"
            ]
          },
          "task-failed": {
            "message": "The task failed! Uh-oh...",
            "plugins": [
              "irc",
              "smtp",
            ],
            "nicks": [
              "sheehan",
              "rail",
            ],
            "emails": [
              "csheehan@mozilla.com",
            ],
            "ids": [
                "id1",
                "id2",
            ]
          }
        }
      }

### IDs

To provide simpler defaults for notifications, 'ids' can be configured within the service. These ids provide default settings for the section in which they are specified. The service loads the ids from a YAML file on startup. If a valid id is present in a notification section (ie task-completed), the application will overwrite the section with the defaults specified in the service. For example if the definition for two ids is,

    id1:
        plugins:
            - irc
            - ses
        channels:
            - "#chan1"
        emails:
            - example@mozilla.com
    id2:
        plugins:
            - log_collect
            
and the task definition above comes through the application on the "task-failed" exchange, the application will notify twice based on these configurations:

    "task-failed": {
        "message": "The task failed! Uh-oh...",
        "plugins": [
          "irc",
          "ses",
        ],
        "nicks": [
          "sheehan",
          "rail",
        ],
        "emails": [
          "example@mozilla.com",
        ],
        "channels": [
          "#chan1"
        ],
        "ids": [
            "id1",
            "id2",
        ]
      }

and

    "task-failed": {
        "message": "The task failed! Uh-oh...",
        "plugins": [
          "log_collect",
        ],
        "nicks": [
          "sheehan",
          "rail",
        ],
        "emails": [
          "example@mozilla.com",
        ],
        "channels": [
          "#chan1"
        ],
        "ids": [
            "id1",
            "id2",
        ]
      }

### Plugins
#### API/Creating Plugins

Pulse-Notifier can be extended to add new functionality by adding a plugin. To create a plugin, create a class named Plugin that extends the BasePlugin class. To implement your functionality, create a method with the following signature:

        async def notify(self, body, envelope, properties, task, task_id, taskcluster_exchange, exchange_config):

Where body, envelope and properties are objects passed from AMQP, task is a dict representation of the task, task_id is the taskcluster task id, taskcluster_exchange is the name of the exchange the message passed through, and exchange_config is the desired notification configuration. 

To add the plugin to the application, put the class in it's own file and add the file to the plugins directory.

##### Base Plugins
- BasePlugin
    Defines the 'name' property for the plugin as the filename the plugin is found in. Also defines the task_info and get_log_urls helper functions.

- AWSPlugin
    An extension of BasePlugin, with added Amazon Web Services key fields.


#### Existing Plugins
- smtp
    Send an email using a SMTP server.
- ses
    Send an email using Amazon SES.
- sns
    Send a notification to an Amazon SNS topic.
- log_collect
    Collect log artifacts from the task and upload to an Amazon S3 bucket (supports aws-provisioner-v1 and buildbot-bridge ProvisionerId's)
- irc
    Push colour-coded messages to internet relay chat.

## Deployment

### Heroku
To deploy to Heroku, cd into the project directory and run
    
    $ heroku git:remote -a <heroku app name>
    $ git push heroku master

This will create a new git remote called 'heroku' where you can push your code. The configuration variables in the sample_env_config file can be added via

    $ heroku config:set KEY=VALUE [KEY2=VALUE2, ....]

You can then use the following to create instances of the service:

    $ heroku ps:scale worker=<number of instances>
    
### Docker

To build the docker image, run

    $ docker build -t pulse-notify ./

To run the image, put all the configuration environment variables (detailed below) in a file and run

    $ docker run --rm --env-file=.env_config pulse-notify:latest

### Config/Environment Variables

The system is configured using a set of environment variables, detailed below:

- PN_SERVICES
    Colon-separated list of enabled plugins.
    
- ID_ENV
    Specifies whether to pull dev or prod id configs

- PULSE_HOST, PULSE_LOGIN, PULSE_PASSWORD, PULSE_SSL, PULSE_PORT, PULSE_QUEUE
    Login information for Mozilla Pulse.

- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    Amazon Web Services login information.

- SNS_ARN
    Amazon Resource Number of SNS topic for sns plugin.

- SMTP_EMAIL, SMTP_PASSWD, SMTP_HOST, SMTP_PORT
    SMTP configuration for smtp plugin.

- S3_BUCKET
    Amazon S3 bucket name for logs.

- SES_EMAIL
    Sender email for SES plugin.

- IRC_HOST, IRC_NAME, IRC_PORT, IRC_NICK, IRC_CHAN, IRC_PASS
    IRC configuration for irc plugin.

- INFLUXDB_NAME, INFLUXDB_HOST, INFFLUXDB_RECORD
    Host, db name and on/off switch for InfluxDB time series data

## Tests
Tests can be run with 

    $ py.test
