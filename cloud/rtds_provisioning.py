import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys

n_pmu_analog_channels = 8  # determined by number of chanells in DAQ
n_pmu_streams_to_cloud = 40  # 8x5 from each channel with have magn, ang, freq, rocof, time, ... (?)

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4", "rtds5", "rtds6", "rtds7", "rtds8", "rtds9", "rtds10", "rtds11", "rtds12", "rtds13", "rtds14", "rtds15", "rtds16", "rtds17", "rtds18"])
rtds_signals = np.array(["pload2", "qload2", "pload3", "qload3", "pload4", "qload4", "pload5", "qload5", "pload6", "qload6", "pload7", "qload7", "pload8", "qload8", "pload9", "qload9", "pload10", "qload10"])

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "rtds001"

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

for r in np.arange(len(rtds_signals)):
    rs = rtds_signals[r]
    value = {"value": 0.0}
    d2 = {rs: value}
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

for ch in np.arange(len(rtds_names)):
    value1 = rtds_names[ch]
    value2 = rtds_signals[ch]
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

for r in np.arange(len(rtds_names)):
    rs = rtds_signals[r]
    value2 = rs
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
for r in np.arange(len(rtds_names)):
    rn = rtds_names[r]
    test_payload += rn + "|" + "0.0"
    if not r == len(rtds_names)-1:
        test_payload += "|"

print("test_payload: \n" + str(test_payload))

ret = client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)
