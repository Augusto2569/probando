import copy
import sys
import signal
import RPi.GPIO as GPIO
import time
import threading
import Adafruit_DHT
import datetime
import random
import json

from datetime import date
from time import sleep
from threading import Semaphore
import paho.mqtt.client as mqtt

DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4

Motor1A = 24
Motor1B = 23
Motor1E = 25

BUTTON_GPIO = 16
LED_GPIO = 20

bluePin = 18
greenPin = 27
redPin = 17

temperature = None
should_blink = False

sem = Semaphore()

# ----------------DATOS MQTT---------------------------
ROOM_ID = "Room1"
CONFIG_TOPIC = "hotel/rooms/" + ROOM_ID + "/config"

MQTT_SERVER = "34.175.247.221"
MQTT_PORT = 1884

TELEMETRY_TOPIC = "hotel/rooms/" + ROOM_ID + "/telemetry/"
TEMPERATURE_TOPIC = TELEMETRY_TOPIC + "temperature"
AIR_CONDITIONER_TOPIC = TELEMETRY_TOPIC + "air-conditioner"
PRESENCE_TOPIC = TELEMETRY_TOPIC + "presence"

COMMAND_TOPIC = "hotel/rooms/" + ROOM_ID + "/command/"
TEMPERATURE_COMMAND_TOPIC = COMMAND_TOPIC + "temperature"
AIR_COMMAND_TOPIC = COMMAND_TOPIC + "air-conditioner"
PRESENCE_COMMAND_TOPIC = COMMAND_TOPIC + "presence"

sensors = {}
current_json_air = ""
current_json_temperature = ""
is_connected = False


# --------------------RASPBERRY--------------------------


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DHT_PIN, GPIO.OUT)

    GPIO.setup(Motor1A, GPIO.OUT)
    GPIO.setup(Motor1B, GPIO.OUT)
    GPIO.setup(Motor1E, GPIO.OUT)

    GPIO.setup(redPin, GPIO.OUT)
    GPIO.setup(greenPin, GPIO.OUT)
    GPIO.setup(bluePin, GPIO.OUT)

    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # configuramos el puerto para el botón
    GPIO.setup(LED_GPIO, GPIO.OUT)
    GPIO.setwarnings(False)


def loop():
    global temperature
    global should_blink
    global current_json_air

    pwm = GPIO.PWM(Motor1A, 100)
    pwm.start(0)
    while True:
        try:
            sem.acquire()
            temperature_copy = copy.deepcopy(temperature)
            sem.release()

            if temperature_copy is not None and should_blink is True:

                if 21 <= temperature_copy <= 24:

                    GPIO.output(Motor1A, GPIO.LOW)
                    pwm.ChangeDutyCycle(0)
                    GPIO.output(Motor1E, GPIO.LOW)

                    json_air = json.dumps({"air_conditioner": {
                                                    "active": False,
                                                    "value": 0}})

                elif temperature_copy < 21:
                    potencia = (21 - temperature_copy) * 10
                    if potencia > 100:
                        potencia = 100
                    GPIO.output(Motor1A, GPIO.HIGH)
                    GPIO.output(Motor1B, GPIO.LOW)
                    pwm.ChangeDutyCycle(potencia)
                    GPIO.output(Motor1E, GPIO.HIGH)

                    json_air = json.dumps({"air_conditioner": {
                                                    "active": True,
                                                    "value": potencia}})


                elif temperature_copy > 24:
                    potencia = (temperature_copy - 24) * 10
                    if potencia > 100:
                        potencia = 100
                    GPIO.output(Motor1A, GPIO.HIGH)
                    GPIO.output(Motor1B, GPIO.LOW)
                    pwm.ChangeDutyCycle(potencia)
                    GPIO.output(Motor1E, GPIO.HIGH)


                    json_air = json.dumps({"air_conditioner": {
                                                    "active": True,
                                                    "value": potencia}})
            if should_blink is False:
                GPIO.output(Motor1A, GPIO.LOW)
                GPIO.output(Motor1B, GPIO.LOW)
                GPIO.output(Motor1E, GPIO.LOW)

                json_air = json.dumps({"air_conditioner": {
                                                    "active": False,
                                                    "value": 0}})

            if current_json_air != json_air:
                client.publish(AIR_CONDITIONER_TOPIC, payload=json_air, qos=0, retain=False)
                print("Published", json_air, "in ", AIR_CONDITIONER_TOPIC)
                current_json_air = copy.deepcopy(json_air)

            time.sleep(3)

        except:
            print("Parada motor")


def weatherSensor():
    global temperature
    global should_blink
    global current_json_temperature
    try:
        while True:
            if should_blink is True:

                today = date.today()
                now = datetime.datetime.now().time()

                sem.acquire()
                humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
                temperature_copy = copy.deepcopy(temperature)
                sem.release()

                if humidity is not None and temperature_copy is not None:

                    print('Temp={0:0.1f}*C Humidity={1:0.1f}%'.format(temperature_copy, humidity))
                    json_temperature = json.dumps({"temperature": {
                                                        "active": True,
                                                        "value": temperature_copy}})
                    if current_json_temperature != json_temperature:

                        client.publish(TEMPERATURE_TOPIC, payload=json_temperature, qos=0, retain=False)
                        print("Published", json_temperature, "in", TEMPERATURE_TOPIC)
                        current_json_temperature = copy.deepcopy(json_temperature)
                else:
                    print("Sensore failure. Check wiring.")

                time.sleep(3)

    except:
        print("Parada temperatura")


def led_lightning():
    global temperature
    while True:

        sem.acquire()
        temperature_copy = copy.deepcopy(temperature)
        sem.release()
        if temperature_copy is not None and should_blink is True:
            if 21 <= temperature_copy <= 24:
                print("verde")
                GPIO.output(bluePin, GPIO.LOW)
                GPIO.output(redPin, GPIO.LOW)
                GPIO.output(greenPin, GPIO.HIGH)
                sleep(3)

            elif temperature_copy < 21:
                print("rojo")
                GPIO.output(bluePin, GPIO.LOW)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(redPin, GPIO.HIGH)
                sleep(3)

            elif temperature_copy > 24:
                print("azul")
                GPIO.output(bluePin, GPIO.HIGH)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(redPin, GPIO.LOW)

                sleep(3)
        elif should_blink is False:
            GPIO.output(bluePin, GPIO.LOW)
            GPIO.output(greenPin, GPIO.LOW)
            GPIO.output(redPin, GPIO.LOW)


def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)


def button_pressed_callback(channel):
    global should_blink
    should_blink = not should_blink


def button():
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=button_pressed_callback, bouncetime=200)
    json_presence = json.dumps(
            {"presence": {
                "active": True,
                "detected": should_blink
                }
            })
    client.publish(PRESENCE_TOPIC, payload=json_presence, qos=0, retain=False)
    print("Published", json_presence, "in ", PRESENCE_TOPIC)


def destroy():
    GPIO.cleanup()


# -----------------------------MQTT--------------------------------
def randomize_sensors():
    global sensors
    sensors = {
        "air_conditioner": {
            "active": True if random.randint(0, 1) == 1 else False,
            "value": random.randint(10, 30)
        },
        "presence": {
            "active": True if random.randint(0, 1) == 1 else False,
            "detected": True if random.randint(0, 1) == 1 else False
        },
        "temperature": {
            "active": True if random.randint(0, 1) == 1 else False,
            "value": random.randint(0, 40)
        }
    }




def on_publish(client, userdata, result):
    print("Data published")


def on_connect(client,  userdata, flags, rc):

    print("Raspy connected with code", rc)
    client.suscribe(AIR_COMMAND_TOPIC)
    print("Subscribed to ", AIR_COMMAND_TOPIC)


def on_message(client, userdata, msg):
    print("Mensaje recibido en raspberry", msg.topic, "con mensaje", msg.payload.decode())
    topic = msg.topic.split('/')
    if "config" in topic:
        global is_connected
        is_connected = True
    elif "command" in topic:
        if topic[-1] == "air-conditioner":
            global sensors
            print("RECIBIDO COMANDO DE AIRE ACONDICIONADO")
            payload = json.loads(msg.payload.decode())
            sensors["air_conditioner"]["mode"] = payload["mode"]


def connect_mqtt():
    client.username_pw_set(username="dso_server", password="dso_password")
    client.on_publish = on_publish
    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(MQTT_SERVER, MQTT_PORT, 60)


# ----------------------------MAIN---------------------------


if __name__ == "__main__":
    setup()
    client = mqtt.Client()
    connect_mqtt()

    try:

        hilo_sensor = threading.Thread(target=weatherSensor, daemon=True)
        hilo_motor = threading.Thread(target=loop, daemon=True)
        hilo_led = threading.Thread(target=led_lightning, daemon=True)
        hilo_boton = threading.Thread(target=button, daemon=True)

        hilo_motor.start()
        hilo_sensor.start()
        hilo_led.start()
        hilo_boton.start()

        hilo_sensor.join()
        hilo_motor.join()
        hilo_led.join()
        hilo_boton.join()

        signal.pause()
    except (KeyboardInterrupt, SystemExit):
        print("Se ha parado por teclado")
        destroy()
        sys.exit()

    destroy()
