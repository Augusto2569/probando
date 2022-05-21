import json
import os
import subprocess
import time
import random
import threading
import copy

import paho.mqtt.client as mqtt

RANDOMIZE_SENSORS_INTERVAL = 60
MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
MQTT_PORT_1 = int(os.getenv("MQTT_SERVER_PORT_1"))
MQTT_PORT_2 = int(os.getenv("MQTT_SERVER_PORT_2"))


TELEMETRY_TOPIC = "hotel/rooms/+/telemetry/"

TEMPERATURE_TOPIC = TELEMETRY_TOPIC + "temperature"
PRESENCE_TOPIC = TELEMETRY_TOPIC + "presence"
AIR_CONDITIONER_TOPIC = TELEMETRY_TOPIC + "air-conditioner"

room_number = ""
sensors = {}

index_room = 1
flag = 0
is_connected = False

current_temperature = ""
current_air_conditioner = ""
current_presence = ""
current_air_conditioner_mode = ""

air_conditioner_mode = ""


client_1883 = mqtt.Client()


def randomize_sensors():
    global sensors
    sensors = {
        "air_conditioner": {
            "active": True if random.randint(0, 1) == 1 else False,
            "mode": 2, # warm = 1, cold = 0, off = 2
            "level": random.randint(0, 40)
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

    if sensors["temperature"]["value"] < 24:
        sensors["air_conditioner"]["mode"] = 0
    elif  sensors["temperature"]["value"] > 25:
            sensors["air_conditioner"]["mode"] = 1




def get_host_name():
    bashCommandName = 'echo $HOSTNAME'
    host = subprocess.check_output(['bash', '-c', bashCommandName]).decode("utf-8")[0:-1]
    return host


def on_publish_1883(client_1883, userdata, result):
    print("Data published Message Router")
    print("-"*40)


def on_publish_1884(client_1884, userdata, result):
    print("DATA PUBLISHED RASPY")
    print("-"*40)


def on_connect_1883(client_1883, userdata, flags, rc):
    print("Mqtt 1883 connected with code, ", rc, "THREAD", threading.current_thread().ident)

    config_topic = "hotel/rooms/" + get_host_name() + "/config"

    client_1883.publish(config_topic, payload=get_host_name(), qos=0, retain=False)

    print("Enviado el id ", get_host_name(), " al topic ", config_topic)
    client_1883.subscribe(config_topic+"/room")
    print("Subscribed to ", config_topic+"/room")


    air_command_topic = "hotel/rooms/+/prueba/air-conditioner"
    client_1883.subscribe(air_command_topic)
    print("Subscribed to ", air_command_topic)



def on_connect_1884(client_1884, userdata, flags, rc):

    print("MQTT 1884 connected with code", rc, "THREAD", threading.current_thread().ident)

    client_1884.subscribe(TEMPERATURE_TOPIC)
    print("Subscribed to ", TEMPERATURE_TOPIC)

    client_1884.subscribe(AIR_CONDITIONER_TOPIC)
    print("Subscribed to ", AIR_CONDITIONER_TOPIC)

    client_1884.subscribe(PRESENCE_TOPIC)
    print("Subscribed to ", PRESENCE_TOPIC)


def on_message_1883(client_1883, userdata, msg):
    print("Mensaje recibido en MQTT 1883 ", msg.topic, " con mensaje ", msg.payload.decode())
    topic = (msg.topic).split("/")
    print("________TOPIC_________:", topic)
    if "config" in topic:
        global room_number
        room_number = msg.payload.decode()
        print("Room number received as: ", room_number)
    elif "command" in topic:
        print("LEGOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
        if topic[-1] == "air-conditioner":
            global air_conditioner_mode
            print("RECIBIDO COMANDO DE AIRE ACONDICIONADO")
            payload = json.loads(msg.payload)
            air_conditioner_mode = payload["mode"]


def on_message_1884(client, userdata, msg):
    global client_1883

    print("Mensaje recibido en MQTT 1884 ", msg.topic, " con mensaje ", msg.payload.decode())
    topic = (msg.topic).split("/")

    if topic[-1] == "temperature":
        temperature = msg.payload.decode()
        client_1883.publish(msg.topic, payload=temperature, qos=0, retain=False)

    if topic[-1] == "air-conditioner":

        air_conditioner = msg.payload.decode()
        client_1883.publish(msg.topic, payload=air_conditioner, qos=0, retain=False)

    if topic[-1] == "presence":

        presence = msg.payload.decode()
        client_1883.publish(msg.topic, payload=presence, qos=0, retain=False)


def on_disconnect():
    global flag
    flag = -1


def connect_mqtt_1883():
    global client_1883
    print("connect_1883")

    client_1883 = mqtt.Client()
    print("Cliente 1883 creado")
    client_1883.username_pw_set(username="dso_server", password="dso_password")
    client_1883.on_connect = on_connect_1883
    client_1883.on_publish = on_publish_1883
    client_1883.on_message = on_message_1883
    client_1883.on_disconnect = on_disconnect
    client_1883.connect(MQTT_SERVER, MQTT_PORT_1, 60)

    client_1883.loop_start()
    while room_number == "":
        time.sleep(1)
    client_1883.loop_stop()
    print("room number recibido: ", room_number)

    TELEMETRY_TOPIC = "hotel/rooms/"+ room_number +"/telemetry/"
    TEMPERATURE_TOPIC = TELEMETRY_TOPIC + "temperature"
    PRESENCE_TOPIC = TELEMETRY_TOPIC + "presence"
    AIR_CONDITIONER_TOPIC = TELEMETRY_TOPIC + "air-conditioner"

    COMMAND_TOPIC = "hotel/rooms/" + room_number + "/command/"
    TEMPERATURE_COMMAND_TOPIC = COMMAND_TOPIC + "temperature"

    AIR_COMMAND_TOPIC = "hotel/rooms/" + room_number + "/prueba/air-conditioner"

    PRESENCE_COMMAND_TOPIC = COMMAND_TOPIC + "presence"

    # client_1883.subscribe(TEMPERATURE_COMMAND_TOPIC)
    client_1883.subscribe(AIR_COMMAND_TOPIC)
    print("Subscribed to ", AIR_COMMAND_TOPIC)
    # client_1883.subscribe(PRESENCE_COMMAND_TOPIC)

    while room_number == "Room1":
        randomize_sensors()

        json_temperature = json.dumps(
            {"temperature": {
                "active": sensors["temperature"]["active"],
                "value": sensors["temperature"]["value"]}})

        json_air = json.dumps({
            "air_conditioner": {
                "active": sensors["air_conditioner"]["active"],
                "mode": sensors["air_conditioner"]["mode"],
                "level": sensors["air_conditioner"]["level"]}})

        json_presence = json.dumps({
            "presence": {
                "active": sensors["presence"]["active"],
                "detected": sensors["presence"]["detected"]}})

        client_1883.publish(TEMPERATURE_TOPIC, payload=json_temperature, qos=0, retain=False)
        print("Published", json_temperature, "in", TEMPERATURE_TOPIC)
        client_1883.publish(AIR_CONDITIONER_TOPIC, payload=json_air, qos=0, retain=False)
        print("Published", json_air, "in ", AIR_CONDITIONER_TOPIC)
        client_1883.publish(PRESENCE_TOPIC, payload=json_presence, qos=0, retain=False)
        print("Published", json_presence, "in ", PRESENCE_TOPIC)
        time.sleep(60)


def connect_mqtt_1884():
    global air_conditioner_mode, current_air_conditioner_mode
    print("connect_1884")
    while room_number == "":
        print("WAITING ROOM NUMBER")
        time.sleep(5)
    client_1884= mqtt.Client()
    client_1884.username_pw_set(username="dso_server", password="dso_password")
    client_1884.on_connect = on_connect_1884
    client_1884.on_message = on_message_1884
    client_1884.on_publish = on_publish_1884
    client_1884.connect(MQTT_SERVER, MQTT_PORT_2, 60)
    client_1884.loop_start()

    COMMAND_TOPIC = "hotel/rooms/" + room_number + "/command/"
    TEMPERATURE_COMMAND_TOPIC = COMMAND_TOPIC + "temperature"
    AIR_COMMAND_TOPIC = COMMAND_TOPIC + "air-conditioner"
    PRESENCE_COMMAND_TOPIC = COMMAND_TOPIC + "presence"

    while True:
        if air_conditioner_mode != current_air_conditioner_mode:
            client_1884.publish(
                AIR_COMMAND_TOPIC,
                payload=json.dumps({"mode": air_conditioner_mode}),
                qos=0,
                retain=False
            )
            print(('PUBLISHED', air_conditioner_mode, 'IN', AIR_COMMAND_TOPIC))
            current_air_conditioner_mode = copy.deepcopy(air_conditioner_mode)
        time.sleep(1)

    client_1884.loop_stop()










if __name__ == "__main__":

    t1 = threading.Thread(target=connect_mqtt_1883)
    #t2 = threading.Thread(target=connect_mqtt_1884)

    t1.setDaemon(True)
    #t2.setDaemon(True)

    t1.start()
    #t2.start()

    t1.join()
    #t2.join()