import socket
import sys
import os
import struct
from datetime import datetime, timedelta
import paho.mqtt.client as paho
import time
import psycopg2
import numpy as np
from pprint import pprint as pp
import platform
import re

# import own RPI2 scripts
from tofloat import tofloat
from send import send
from receive import receive
from settings import settings_fromRTDS, settings_toRTDS, NumData, default_accuracy, dbname
from settings import IP_send, IP_receive, Port_send, Port_receive


# subscribe to the setpoints from the cloud and receive them
# (any storing in DB for grafana necessary?)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/TEF/inverter001/cmd") # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("Topic: " + msg.topic+" Payload: "+str(msg.payload))

    now = datetime.utcnow()

    entire_str = msg.payload.decode("utf-8")
    Pset5 = float(entire_str.replace("inverter001@setpoint|", ""))

    data_to_RTDS = [Pset5, -0.2, 0.7, 0.5, 0.1, 0.9, -0.96, -0.6]
    send(data_to_RTDS, IP_send, Port_send)


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


client = paho.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("10.12.0.10", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
