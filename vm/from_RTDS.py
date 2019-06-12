import numpy as np
import paho.mqtt.client as paho
import time

# import own RPI2 scripts
from vm.receive import receive
from vm.settings import *

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4", "rtds5", "rtds6", "rtds7", "rtds8", "rtds9", "rtds10", "rtds11", "rtds12", "rtds13", "rtds14", "rtds15", "rtds16", "rtds17", "rtds18"])
rtds_signals = np.array(["pload2", "qload2", "pload3", "qload3", "pload4", "qload4", "pload5", "qload5", "pload6", "qload6", "pload7", "qload7", "pload8", "qload8", "pload9", "qload9", "pload10", "qload10"])

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "rtds001"

cloud_ip = "10.12.0.10"
# cloud_ip = "127.0.0.1"
broker_ip = cloud_ip
port = 1883
api_key = "asd1234rtds"


def on_publish(client, userdata, result):  # create function for callback
    print("My data published! \n")
    pass


def storedata_attempt():
    # receive from RTDS:
    npdata = np.array(receive(IP_receive, Port_receive, NumData))
    print("Values received from RTDS: ", npdata)

    # build message
    test_payload = ""
    for r in np.arange(len(rtds_names)):
        rn = rtds_names[r]
        value = npdata[r]
        test_payload += rn + "|" + str(value)
        if not r == len(rtds_names) - 1:
            test_payload += "|"
    print("current_payload: \n" + str(test_payload))

    # publish to the cloud:
    client1 = paho.Client("control1")  # create client object
    client1.on_publish = on_publish  # assign function to callback
    client1.connect(broker_ip, port)  # establish connection
    client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)


def storedata_once():
    while True:
        try:
            storedata_attempt()
        except:
            print("Unexpected error:", sys.exc_info())
            # logging.error(" When: " + str(datetime.now()) + " --- " + "Error in storedataOnce(): ", sys.exc_info())
            pass
        else:
            break


def storedata_repeatedly():
    while True:
        storedata_once()
        # time.sleep(0.1)


storedata_repeatedly()
