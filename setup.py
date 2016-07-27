from setuptools import setup, find_packages

with open('requirements.txt', 'r') as reqs_txt:
    reqs = reqs_txt.readlines()
try:
    with open('README.md', 'r') as readme_txt:
        readme = readme_txt.read()
except FileNotFoundError:
    readme = 'No README.md found.'

setup(
    name='pulse-notify',
    version='0.2',
    packages=find_packages(),
    url='https://github.com/cgsheeh/pulse-notify',
    license='',
    author='Connor Sheehan',
    author_email='csheehan@mozilla.com',
    description='Sends notifications based on taskcluster task statuses.',
    long_description=readme,
    install_requires=reqs,
    entry_points="""
        [console_scripts]
        pulse-notify = pulsenotify.main:cli
      """,
)
