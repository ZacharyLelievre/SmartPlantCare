from idlelib.pyshell import PORT

import paho.mqtt.client as mqtt

BROKER="172.20.10.8"

port=1883
TOPIC="sensor/temperature"

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)

sensor_data = {"temperature": [], "humidity": []}

def on_message(client, userdata, msg):
    data = msg.payload.decode().split(',')
    temperature, humidity = float(data[0]), float(data[1])
    sensor_data["temperature"].append(temperature)
    sensor_data["humidity"].append(humidity)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, TOPIC)
client.loop_start()