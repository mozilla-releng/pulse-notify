from setuptools import setup

setup(
    name='pulse-notify',
    version='0.1',
    packages=['pulsenotify'],
    url='',
    license='',
    author='Rail Aliiev',
    author_email='rail@mozilla.com',
    description='',
    requires=[
        'aioamqp',
        'aiohttp',
        'blessings',
    ],
)
