import socket
import sys
import os
import struct
from datetime import datetime, timedelta
import paho.mqtt.client as paho
import multiprocessing
import numpy as np
from random import random
import time
from send import send
from settings import *

manager = multiprocessing.Manager()

# Default values
data_to_RTDS = manager.list([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 50.0, 10.0])


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("modify_f_v") # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("Topic: " + msg.topic+" Payload: "+str(msg.payload))

    entire_str = msg.payload.decode("utf-8")
    test_payload = "f50|v10|end"
    #entire_str = test_payload
    print(entire_str)
    f = find_between(entire_str, "f", "|v")
    v = find_between(entire_str, "v", "|end")
    print(f)
    print(v)
    try:
        data_to_RTDS[11] = float(f)
        data_to_RTDS[12] = float(v)
    except ValueError:
        print("Cannot convert the message!")


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def mqtt_loop():
    client = paho.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    print('mqtt loop: starting')
    client.loop_forever()


def send_to_RTDS():
    print('Sending to RTDS: starting')
    while True:
        send(data_to_RTDS, IP_send, Port_send)
        print("Sent." + str(data_to_RTDS))
        time.sleep(5.0)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=mqtt_loop)
    p1.start()
    p2 = multiprocessing.Process(target=send_to_RTDS)
    p2.start()
    p1.join()
    p2.join()
