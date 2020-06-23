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
from csv import writer

manager = multiprocessing.Manager()

# Default values
data_received = manager.list(default_controls)  # with min_ts to pass

# file for results accessible from controller:
with open('results_vm2rtds.csv', 'w', newline='') as file:
    csv_writer = writer(file)
    csv_writer.writerow(["ts_pdc", "ts_execute"])


def append_list_as_row(file_name, list_of_elem):
    with open(file_name, 'a+', newline='') as file:
        csv_writer = writer(file)
        csv_writer.writerow(list_of_elem)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/asd1234rtds/rtds001/cmd")  # Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # print("Topic: " + msg.topic+" Payload: "+str(msg.payload))
    entire_str = msg.payload.decode("utf-8")

    if "rtds001@sc_brk1|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk1|", ""))
        data_received[0] = value
    elif "rtds001@sc_brk2|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk2|", ""))
        data_received[1] = value
    elif "rtds001@sc_brk3|" in entire_str:
        value = float(entire_str.replace("rtds001@sc_brk3|", ""))
        data_received[2] = value
    elif "rtds001@pref1|" in entire_str:
        value = float(entire_str.replace("rtds001@pref1|", ""))
        data_received[3] = value
    elif "rtds001@pref2|" in entire_str:
        value = float(entire_str.replace("rtds001@pref2|", ""))
        data_received[4] = value
    elif "rtds001@pref3|" in entire_str:
        value = float(entire_str.replace("rtds001@pref3|", ""))
        data_received[5] = value
    elif "rtds001@qref1|" in entire_str:
        value = float(entire_str.replace("rtds001@qref1|", ""))
        data_received[6] = value
    elif "rtds001@qref2|" in entire_str:
        value = float(entire_str.replace("rtds001@qref2|", ""))
        data_received[7] = value
    elif "rtds001@qref3|" in entire_str:
        value = float(entire_str.replace("rtds001@qref3|", ""))
        data_received[8] = value
    elif "rtds001@ts_pdc|" in entire_str:
        data_received[9] = entire_str.replace("rtds001@ts_pdc|", "")
    elif "rtds001@desc|" in entire_str:
        data_received[10] = entire_str.replace("rtds001@desc|", "")
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
    mem_ts_pdc = 0
    while True:
        curr_data_received = data_received
        data_to_RTDS = curr_data_received[0:-2]
        if mem_ts_pdc == curr_data_received[-2]:
            continue
        print("TS_PDC in received data (no-reps): " + str(curr_data_received[-2]))
        ts_execute = round(datetime.utcnow().timestamp() * 1000, 0)
        send(data_to_RTDS, IP_send, Port_send)  # substitute last with 0 due to ts
        print("\tSent values at ts="+str(ts_execute)+" : " + str(data_to_RTDS) +
              " with delay to ts_pdc (not min_ts!): " + str(ts_execute-float(mem_ts_pdc)) + "ms")

        append_list_as_row("results_vm2rtds.csv", [mem_ts_pdc, ts_execute])

        mem_ts_pdc = curr_data_received[-2]
        # time.sleep(0.01)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=mqtt_loop)
    p1.start()
    p2 = multiprocessing.Process(target=send_to_RTDS)
    p2.start()
    p1.join()
    p2.join()
