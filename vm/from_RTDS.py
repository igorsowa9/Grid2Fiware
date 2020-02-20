import numpy as np
import paho.mqtt.client as paho
import time
from datetime import datetime
import pandas as pd

# import own RPI2 scripts
from receive import receive
from settings import *

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4"])
rtds_text = np.array(["ts1", "add1"])

rtds_signals = np.array(["p2meas", "q2meas", "p3meas", "q3meas"])
rtds_tsignals = np.array(["ts_measurement", "notes"])
NumData_fromRTDS = 4

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "rtds001"

cloud_ip = "10.12.0.10"
# cloud_ip = "127.0.0.1"
broker_ip = cloud_ip
port = 1883
api_key = "asd1234rtds"


def on_publish(client, userdata, result):  # create function for callback
    # print("My data published! \n")
    pass

def storedata_attempt(client1):
    global c
    # receive from RTDS:
    npdata = np.round(np.array(receive(IP_receive, Port_receive, NumData_fromRTDS)),4)
    other_data = np.array([datetime.now().timestamp(), pd.Timestamp(datetime.now().timestamp(), unit='s')])
    print("Values received from RTDS: ", npdata)
    print("other_data: ", other_data)

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

    print("current_payload: \n" + str(test_payload))

    # publish to the cloud:
    client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)
    

def storedata_once(client1):
    while True:
        storedata_attempt(client1)
#        try:
#            storedata_attempt()
#        except:
#            print("Unexpected error:", sys.exc_info())
#            # logging.error(" When: " + str(datetime.now()) + " --- " + "Error in storedataOnce(): ", sys.exc_info())
#            pass
#        else:
#            break


def storedata_repeatedly():
    client1 = paho.Client("control1")  # create client object
    client1.on_publish = on_publish  # assign function to callback
    client1.connect(broker_ip, port)  # establish connection
    while True:
        storedata_once(client1)
        time.sleep(0.1)


storedata_repeatedly()
