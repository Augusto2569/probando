FROM python:3.7.3

COPY /app /etc/usr/src/app

WORKDIR /etc/usr/src/app

RUN pip install Flask Flask-Cors requests
RUN pip install paho-mqtt
RUN pip install requests

CMD ["python", "message_router.py"]