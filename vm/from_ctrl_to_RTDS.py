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

data_to_RTDS = manager.list([0.01, 0.01])


# subscribe to the setpoints from the cloud and receive them
# (any storing in DB for grafana necessary?)
# The callback for when the client receives a CONNACK response from the server.


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/asd1234rtds/rtds001/cmd") # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # print("Topic: " + msg.topic+" Payload: "+str(msg.payload))

    now = datetime.utcnow()
    entire_str = msg.payload.decode("utf-8")

    if "rtds001@setpoint1|" in entire_str:
        value = float(entire_str.replace("rtds001@setpoint1|", ""))
        data_to_RTDS[0] = value
    elif "rtds001@setpoint2|" in entire_str:
        value = float(entire_str.replace("rtds001@setpoint2|", ""))
        data_to_RTDS[1] = value
    else:
        print("another setpoint than exepcted")


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
    client.connect("10.12.0.10", 1883, 60)
    print('mqtt loop: starting')
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()


def send_to_RTDS():
    print('send to RTDS: starting')
    while True:
        print(data_to_RTDS[0])
        send(data_to_RTDS, IP_send, Port_send)
        time.sleep(0.5)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=mqtt_loop)
    p1.start()
    p2 = multiprocessing.Process(target=send_to_RTDS)
    p2.start()
    p1.join()
    p2.join()
