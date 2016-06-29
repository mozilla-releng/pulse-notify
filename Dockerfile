FROM python:3.5-onbuild
MAINTAINER csheehan@mozilla.com

RUN python setup.py install
CMD [ "python", "pulsenotify/main.py", "-v" ]
