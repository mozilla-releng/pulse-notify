from setuptools import setup

setup(
    name='pulse-notify',
    version='0.2',
    packages=['pulsenotify'],
    url='',
    license='',
    author='Rail Aliiev, Connor Sheehan',
    author_email='rail@mozilla.com',
    description='',
    install_requires=[
        'aioamqp',
        'aiohttp',
        'blessings',
        'boto3',
        'uvloop',
    ],
    entry_points="""
        [console_scripts]
        pulse-notify = pulsenotify.main:cli
      """,

)
