# Pulse-Notifier

Pulse-Notifier is used to take various actions based on the completion status of Taskcluster tasks, primarily notifications for failures and other important events. The program depends on the Taskcluster and Pulse tools at Mozilla.

### Technical Features
- Asynchronous Python 3.5
- Asynchronous AMQP consumer for Pulse messages
- Easily extended via drop-in style plugins, due to dependency injection

## Core

Pulse-Notifier is an asynchronous event loop with an AMQP consumer listening for Taskcluster events on Mozilla Pulse. The consumer receives a message about the status of the task and parses the task definition for notification information. Based on the notification information, the consumer passes the necessary information to various channels of communication/action, called 'plugins'.




### Task Definition

To recieve a notification from a task, the task definition must include an 'extra' section, with a 'notifcation' subsection. Within the notification section, each unique task status has it's notification configuration defined. Possible task statuses are:

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
- emails: emails to be notified for (ses and smtp plugins only)
- nicks: IRC nicknames to notify (irc plugin only)

The fields subject and message are not required, a simple fallback message is enabled. Emails and nicks are also not necessary, the service will still try to notify regardless. Below is an example task definition:

    "extra": {
        "notification": {
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
              "ses",
            ],
            "nicks": [
              "sheehan",
              "rail",
            ],
            "emails": [
              "csheehan@mozilla.com",
            ]
          }
        }
      }

### Plugins

#### API/Creating Plugins

Pulse-Notifier can be extended to add new functionality by adding a plugin. To create a plugin, create a class named Plugin that extends the BasePlugin class. To implement your functionality, create a method with the following signature:

        async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange)

Where channel, envelope and properties are objects passed by the basic_consume method, body is the json object passed by basic_consume converted to a dict, task is a dict representation of the task, and taskcluster_exchange is the name of the exchange the message passed through. To add the plugin to the application, put the class in it's own file and add the file to the plugins directory.

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
    Collect log artifacts from the task and upload to an Amazon S3 bucket.
- irc
    Push colour-coded messages to internet relay chat.
- repulse
    Publish an AMQP message to Pulse.

### System Configuration

The system is configured using a set of environment variables, detailed below:

- PN_SERVICES
    Colon-separated list of enabled plugins.

- PULSE_HOST, PULSE_LOGIN, PULSE_PASSWORD, PULSE_SSL, PULSE_PORT, PULSE_QUEUE
    Login information for Mozilla Pulse.

- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    Amazon Web Services login information.

- SNS_ARN
    Amazon Resource Number of SNS topic for sns plugin.

- SMTP_EMAIL, SMTP_PASSWD, SMTP_HOST, SMTP_PORT, SMTP_TEMPLATE
    SMTP configuration for smtp plugin.

- S3_BUCKET
    Amazon S3 bucket name for logs.

- SES_EMAIL
    Confirmed email for SES (testing only).

- IRC_HOST, IRC_NAME, IRC_PORT, IRC_NICK, IRC_CHAN, IRC_PASS
    IRC configuration for irc plugin.

- FLUX_RECORD
    Boolean switch for logging of InfluxDB time-series data (ie performance metrics)

## Tests

Tests can be run with

    $ py.test