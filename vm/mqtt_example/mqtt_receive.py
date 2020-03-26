from datetime import datetime, timedelta
import paho.mqtt.client as paho


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/" + "asd123pub" + "/" + "aef324fq" + "/attrs")


def on_message(client, userdata, msg):
    now = datetime.utcnow()
    payload = msg.payload.decode("utf-8")  # decode to string type if necessary
    print("Message received ("+str(now)+"). Topic: " + msg.topic+" Payload: "+str(payload))


client = paho.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)

client.loop_forever()
