import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys

n_pmu_analog_channels = 8  # determined by number of chanells in DAQ
n_pmu_streams_to_cloud = 40  # 8x5 from each channel with have magn, ang, freq, rocof, time, ... (?)

channel_names = np.array(["ch1", "ch2", "ch3", "ch4", "ch5", "ch6"])
sub_names = np.array(["a", "b", "c", "d", "e"])

channel_signals = np.array(["v1a", "v3a", "v5a", "v8a", "v9a", "v10a"])
sub_signals = np.array(["magnitude", "frequency", "angle", "rocof", "timestamp"])

fiware_service = "grid_uc"
device_type = "PMU"
device_id = "pmu001"

cloud_ip = "10.12.0.10"
# cloud_ip = "127.0.0.1"
broker_ip = cloud_ip
port = 1883
api_key = "asd1234"


def on_publish(client,userdata,result):             #create function for callback
    print("My data published! \n")
    pass


## provisioning device>mqtt borker>orion>quantum leap>crate>grafana communication

# 1. pushing the model
print("\n --> 1. data model")

url = 'http://' + cloud_ip + ':1026/v2/entities'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}


d = {
        "id": "Simulation:1",
        "type": device_type}

for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    ch_s = channel_signals[ch]

    for k in sub_signals:
        key = str(ch_s) + "_" + str(k)
        value = {"value": 0.0}
        d2 = {key: value}
        d.update(d2)

# d = {
#         "id": "Simulation:1",
#         "type": device_type,
#         "v1a_magnitude": {
#           "value": 0.0
#         },
#         "v1a_frequency": {
#           "value": 0.0
#         },
#         "v1a_angle": {
#           "value": 0.0
#         },
#         "v1a_rocof": {
#           "value": 0.0
#         },
#         "v1a_timestamp": {
#           "value": 0.0
#         }
# }

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# 2. provisioning a service group for mqtt
print("\n --> 2. provisioning a service group for mqtt")

url = 'http://' + cloud_ip + ':4041/iot/services'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}
d = {
    "services": [
       {
           "apikey": api_key,
           "cbroker": "http://orion:1026",
           "entity_type": device_type,
           "resource": "/iot/d"
       }
    ]
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# 3. provisioning sensors
print("\n --> 3. provisioning sensors")

url = 'http://' + cloud_ip + ':4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

attributes = []

for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    ch_s = channel_signals[ch]

    for sub in np.arange(len(sub_names)):
        sn = sub_names[sub]
        ss = sub_signals[sub]

        value1 = ch_n + sn
        value2 = ch_s + "_" + ss
        di = {"object_id": value1, "name": value2, "type": "Number"}
        attributes.append(di)

d = {
"devices": [
   {
     "device_id":   "" + device_id + "",
     "entity_name": "Simulation:1",
     "entity_type": "" + device_type + "",
     "protocol":    "PDI-IoTA-UltraLight",
     "transport":   "MQTT",
     "timezone":    "Europe/Berlin",
     "attributes": attributes
   }
]
}

# d = {
# "devices": [
#    {
#      "device_id":   "" + device_id + "",
#      "entity_name": "Simulation:1",
#      "entity_type": "" + device_type + "",
#      "protocol":    "PDI-IoTA-UltraLight",
#      "transport":   "MQTT",
#      "timezone":    "Europe/Berlin",
#      "attributes": [
#        {"object_id": "ch1a", "name": "v1a_magnitude", "type": "Number"},
#        {"object_id": "ch1b", "name": "v1a_frequency", "type": "Number"},
#        {"object_id": "ch1c", "name": "v1a_angle", "type": "Number"},
#        {"object_id": "ch1d", "name": "v1a_rocof", "type": "Number"},
#        {"object_id": "ch1e", "name": "v1a_timestamp", "type": "Number"}
#     ]
#    }
# ]
# }

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# 4. making subscriptions of QL
print("\n --> 4. making subscriptions of QL")

url = 'http://' + cloud_ip + ':1026/v2/subscriptions/'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

attrs = []

for ch in np.arange(len(channel_names)):
    ch_s = channel_signals[ch]
    for sub in np.arange(len(sub_names)):
        ss = sub_signals[sub]
        value2 = ch_s + "_" + ss
        attrs.append(value2)

d = {
       "description": "Notification Quantumleap",
       "subject": {
           "entities": [
               {"id": "Simulation:1", "type": device_type}
           ],
           "condition": {
               "attrs": attrs
           }
               },
           "notification": {
                "http": {"url": "http://quantumleap:8668/v2/notify"},
                "attrs": attrs,
            "metadata": ["dateCreated", "dateModifid"]
           },
       "throttling": 0
}

# d = {
#        "description": "Notification Quantumleap",
#        "subject": {
#            "entities": [
#                {"id": "Simulation:1", "type": device_type}
#            ],
#            "condition": {
#                "attrs": [
#                    "v1a_magnitude",
#                    "v1a_frequency",
#                    "v1a_angle",
#                    "v1a_rocof",
#                    "v1a_timestamp"
#                ]
#            }
#                },
#            "notification": {
#                 "http": {"url": "http://quantumleap:8668/v2/notify"},
#                 "attrs": [
#                    "v1a_magnitude",
#                    "v1a_frequency",
#                    "v1a_angle",
#                    "v1a_rocof",
#                    "v1a_timestamp"
#                ],
#             "metadata": ["dateCreated", "dateModifid"]
#            },
#        "throttling": 0
# }

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML


client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker_ip, port)  # establish connection

test_payload = ""
for ch in np.arange(len(channel_names)):
    ch_n = channel_names[ch]
    for sub in np.arange(len(sub_names)):
        sn = sub_names[sub]
        test_payload += ch_n + sn + "|" + "0.0"
        if not (ch == len(channel_names)-1 and sub == len(sub_names)-1):
            test_payload += "|"

print("test command (not executed): \n" + str(test_payload))
print("mosquitto_pub -h "+broker_ip+" -t \"/"+api_key+"/"+device_id+"/attrs\" -m \""+test_payload+"\" ")

# ret = client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)
