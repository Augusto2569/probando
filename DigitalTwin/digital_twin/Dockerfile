FROM python:3.7.3

COPY /app /etc/usr/src/app

WORKDIR /etc/usr/src/app

RUN pip install paho-mqtt


CMD ["python", "digital_twin.py"]