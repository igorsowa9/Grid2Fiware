import numpy as np
import paho.mqtt.client as paho
import time
from datetime import datetime

broker_ip = "localhost"  # IP of the destination machine
port = 1883
api_key = "asd123pub"
device_id = "aef324fq"


def on_publish(client, userdata, result):  # create function for callback
    print("My data published! \n")
    pass


payload_array = np.array(["first message", "second message", "third message"])
print("prepared payload: \n" + str(payload_array) + '\n')

client1 = paho.Client("pub1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker_ip, port)  # establish connection

for p in payload_array:
    now = datetime.utcnow()
    client1.publish("/" + api_key + "/" + device_id + "/attrs", p)
    time.sleep(1)
