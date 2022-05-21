import time, os, json
from flask import Flask, request
from flask_cors import CORS
import paho.mqtt.client as mqtt
import requests
import threading


MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))

TELEMETRY_TOPIC = "hotel/rooms/+/telemetry/"
TEMPERATURE_TOPIC = TELEMETRY_TOPIC + "temperature"
AIR_CONDITIONER_TOPIC = TELEMETRY_TOPIC + "air-conditioner"
PRESENCE_TOPIC = TELEMETRY_TOPIC + "presence"

ALL_TOPICS = TELEMETRY_TOPIC + "+"
CONFIG_TOPIC = "hotel/rooms/+/config"

DATA_INGESTION_API_URL = "http://"+os.getenv("DATA_INGESTION_API_HOST")+":"+os.getenv("DATA_INGESTION_API_PORT")
API_HOST = os.getenv("API_HOST")
API_PORT = os.getenv("API_PORT")
app = Flask(__name__)

index_room = 1
json_temperature = []
json_air = []
json_presence = []


current_temperature = "0"
current_air = "0"
current_presence = "0"
saved_rooms = {}
room_name = ""


def on_connect(client, userdata, flags, rc):
    print("Connected on subscriber with code ", rc)

    client.subscribe(TEMPERATURE_TOPIC)
    print("Subscribed to ", TEMPERATURE_TOPIC)

    client.subscribe(AIR_CONDITIONER_TOPIC)
    print("Subscribed to ", AIR_CONDITIONER_TOPIC)

    client.subscribe(PRESENCE_TOPIC)
    print("Subscribed to ", PRESENCE_TOPIC)


    client.subscribe(ALL_TOPICS)
    client.subscribe(CONFIG_TOPIC)
    print("Subscribed to all")
    print("Subscribed to", CONFIG_TOPIC)


def on_message(client, userdata, msg):
    global current_temperature, current_air, current_presence, index_room, room_name
    print("Mensaje recibido en ", msg.topic, " con mensaje ", msg.payload.decode())
    topic = msg.topic.split('/')
    value = -1
    if topic[-1] == "config":
        if saved_rooms.get(msg.payload.decode()) is None:
            room_name = "Room" + str(index_room)
            saved_rooms[msg.payload.decode()] = room_name
            print("Digital with id", msg.payload.decode(), "saved as", room_name)
            index_room += 1
            client.publish(msg.topic + "/room", payload=room_name, qos=0, retain=True)

            topic = "hotel/rooms/Room1/prueba/air-conditioner"
            json_mode = json.dumps({"mode": 0})
            client.publish(topic, payload=json_mode, qos=0, retain=True)
            print("Publicado", room_name, "en TOPIC", msg.topic + "/room")

    if "telemetry" in topic:
        room_name = topic[2]
        payload = json.loads(msg.payload.decode())
        value = -1
        if topic[-1] == "temperature":
            value = payload["temperature"]["value"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": topic[-1], "value": value}
            )
            """active = payload["temperature"]["active"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": topic[-1], "value": active}
            )"""
        if topic[-1] == "air-conditioner":
            level = payload["air_conditioner"]["level"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": "air-level", "value": level}
            )
            active = payload["air_conditioner"]["active"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": "air-active", "value": active}
            )
            mode = payload["air_conditioner"]["mode"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": "air-mode", "value": mode}
            )
            
        if topic[-1] == "presence":
            value = payload["presence"]["detected"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": topic[-1], "value": value}
            )
            """active = payload["presence"]["active"]
            requests.post(
                DATA_INGESTION_API_URL + "/device_state",
                json={"room": room_name, "type": topic[-1], "value": active}
            )"""


def send_command(params):
    type_dev = params["type"]
    mode = params["value"]
    room = params["room"]
    topic = "hotel/rooms/" + room + "/prueba/air-conditioner"
    if type_dev == "air-conditioner-mode":
        print("TYPE DEVVVVVVVVVVVVVVVVV:", type_dev)
        json_mode = json.dumps({"mode": mode})
        client.publish(topic, payload=json_mode, qos=0, retain=True)
        print("Command message sent through " + topic)
        return {"response": "Message successfully sent"}, 200
    else:
        return {"response": "Incorrect type param"}, 401


@app.route('/device_state', methods=['POST'])
def device_state():
    if request.method == 'POST':
        params = request.get_json()
        return send_command(params)


def mqtt_listener():
    client.loop_forever()


if __name__ == "__main__":
    client = mqtt.Client()
    client.username_pw_set(username="dso_server", password="dso_password")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_SERVER, MQTT_PORT, 60)

    t1 = threading.Thread(target=mqtt_listener)
    t1.setDaemon(True)
    t1.start()
    CORS(app)
    app.run(host=API_HOST, port=API_PORT, debug=True)
