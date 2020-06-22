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
data_to_RTDS = manager.list(default_controls + [0])  # with min_ts to pass


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/asd1234rtds/rtds001/cmd")  # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # print("Topic: " + msg.topic+" Payload: "+str(msg.payload))

    now = datetime.utcnow()
    entire_str = msg.payload.decode("utf-8")
    print(entire_str)
    return
    if "rtds001@sc_brk1|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk1|", ""))
        data_to_RTDS[0] = value
    elif "rtds001@sc_brk2|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk2|", ""))
        data_to_RTDS[1] = value
    elif "rtds001@sc_brk3|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk3|", ""))
        data_to_RTDS[2] = value
    elif "rtds001@pref1|" in entire_str:
        value = float(entire_str.replace("rtds001@pref1|", ""))
        data_to_RTDS[3] = value
    elif "rtds001@pref2|" in entire_str:
        value = float(entire_str.replace("rtds001@pref2|", ""))
        data_to_RTDS[4] = value
    elif "rtds001@pref3|" in entire_str:
        value = float(entire_str.replace("rtds001@pref3|", ""))
        data_to_RTDS[5] = value
    elif "rtds001@qref1|" in entire_str:
        value = float(entire_str.replace("rtds001@qref1|", ""))
        data_to_RTDS[7] = value
    elif "rtds001@qref2|" in entire_str:
        value = float(entire_str.replace("rtds001@qref2|", ""))
        data_to_RTDS[8] = value
    elif "rtds001@qref3|" in entire_str:
        value = float(entire_str.replace("rtds001@qref3|", ""))
        data_to_RTDS[9] = value
    elif "rtds001@ts_min|" in entire_str:
        data_to_RTDS[10] = float(entire_str.replace("rtds001@min_ts|", ""))
    else:
        print("another setpoint than expected")


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
    client.loop_forever()


def send_to_RTDS():
    print('Sending to RTDS: starting')
    while True:
        ts_sendtortds = round(datetime.utcnow().timestamp() * 1000, 0)
        send(data_to_RTDS[0:-1], IP_send, Port_send)
        print("Sent at ts="+str(ts_sendtortds)+": " + str(data_to_RTDS[0:-1]))
        time.sleep(0.1)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=mqtt_loop)
    p1.start()
    # p2 = multiprocessing.Process(target=send_to_RTDS)
    # p2.start()
    p1.join()
    # p2.join()
