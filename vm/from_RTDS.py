import numpy as np
import paho.mqtt.client as paho
import time
from datetime import datetime
import pandas as pd

# import own RPI2 scripts
from receive import receive
from settings import *

fiware_service = "grid_uc"
device_type = "rtds1"
device_id = "rtds001"

cloud_ip = "10.12.0.10"  # if tunelled!
broker_ip = cloud_ip
port = 1883
api_key = "asd1234rtds"


def on_publish(client, userdata, result):
    print("RTDS data published to cloud! \n")
    pass


def storedata_attempt(client1):
    # receive from RTDS:
    npdata = np.round(np.array(receive(IP_receive, Port_receive, NumData_fromRTDS)),4)
    ts_prec = 3
    ts_m = np.round(datetime.now().timestamp(), ts_prec)
    ts_ms = np.round(np.round(datetime.now().timestamp(), ts_prec) * 10**ts_prec)
    other_data = np.array([ts_ms, pd.Timestamp(ts_m, unit='s')])
    print("Values received from RTDS: ", npdata)
    print("Data to be merged: ", other_data)

    # build message
    test_payload = ""
    for r in np.arange(len(rtds_names)):
        rn = rtds_names[r]
        value = npdata[r]
        test_payload += rn + "|" + str(value) + "|"

    for r in np.arange(len(rtds_text)):
        rn = rtds_text[r]
        value = other_data[r]
        test_payload += rn + "|" + str(value)
        if not r == len(rtds_text) - 1:
            test_payload += "|"

    print("Payload before publishing: \n" + str(test_payload))
    client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)
    

def storedata_once(client1):
    while True:
        try:
            storedata_attempt(client1)
        except:
            print("Unexpected error:", sys.exc_info())
            # logging.error(" When: " + str(datetime.now()) + " --- " + "Error in storedataOnce(): ", sys.exc_info())
            pass
        else:
            break


def storedata_repeatedly():
    client1 = paho.Client("control1")  # create client object
    client1.on_publish = on_publish  # assign function to callback
    client1.connect(broker_ip, port)  # establish connection
    while True:
        storedata_once(client1)
        time.sleep(0.1)


storedata_repeatedly()
