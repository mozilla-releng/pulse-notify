from setuptools import setup

with open('requirements.txt', 'r') as reqs_txt:
    reqs = reqs_txt.readlines()

setup(
    name='pulse-notify',
    version='0.2',
    packages=['pulsenotify'],
    url='http://github.com/cgsheeh/pulse-notify',
    license='',
    author='Connor Sheehan',
    author_email='csheehan@mozilla.com',
    description='Sends notifications based on taskcluster task statuses.',
    install_requires=reqs,
    entry_points="""
        [console_scripts]
        pulse-notify = pulsenotify.main:cli
      """,

)
