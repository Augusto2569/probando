FROM debian:buster

RUN apt update && apt upgrade -y

RUN apt install mosquitto mosquitto-clients -y

RUN touch /etc/mosquitto/passwd

RUN mosquitto_passwd -b /etc/mosquitto/passwd dso_server dso_password

EXPOSE 1883

CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]