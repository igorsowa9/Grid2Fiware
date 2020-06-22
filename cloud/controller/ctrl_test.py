import json
import requests
import sys
import time
import numpy as np
from datetime import datetime
import multiprocessing
from controller_config import *
import paho.mqtt.client as paho
import time

rtds_topic = "/asd1234rtds/rtds001/attrs"
pmu_topic = "/asd1234/pmu001/attrs"


# def on_connect_both():
#     pass
#
#
def on_message_both(client, userdata, message):
    print(message.payload.decode("utf-8"))
    print(message.topic)
    print(message.qos)
    print(message.retain)
    pass


client = paho.Client("name1")
client.on_message = on_message_both
client.connect("10.12.0.10")

# client.loop_start()
client.subscribe(rtds_topic)
client.subscribe(pmu_topic)
client.publish(rtds_topic, "wiadomosc1")
client.publish(pmu_topic, "wiadomosc1")
# time.sleep(4)
# client.loop_stop()
client.loop_forever()

# client.on_connect = on_connect_both
# client.subscribe(pmu_topic)
# client.on_message = on_message_both
# client.connect("10.12.0.10", 1883, 60)
# client.loop_forever()
