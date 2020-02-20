import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys

n_pmu_analog_channels = 8  # determined by number of chanells in DAQ
n_pmu_streams_to_cloud = 40  # 8x5 from each channel with have magn, ang, freq, rocof, time, ... (?)

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4"])
rtds_text = np.array(["ts1", "add1"])

rtds_signals = np.array(["p2meas", "q2meas", "p3meas", "q3meas"])
rtds_tsignals = np.array(["ts_measurement", "notes"])

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "rtds001"

cloud_ip = "10.12.0.10"
# cloud_ip = "127.0.0.1"
broker_ip = cloud_ip
port = 1883
api_key = "asd1234rtds"


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

# 3. provisioning sensors and actuatros
print("\n --> 3. provisioning sensors AND acutuators")

url = 'http://' + cloud_ip + ':4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

attributes = []

for ch in np.arange(len(rtds_names)):
    attributes.append({"object_id": rtds_names[ch], "name": rtds_signals[ch], "type": "Number"})

for ch in np.arange(len(rtds_text)):
    attributes.append({"object_id": rtds_text[ch], "name": rtds_tsignals[ch], "type": "Text"})
print(attributes)
d = {
"devices": [
   {
       "device_id":   device_id,  # rtds001
       "entity_name": "Simulation:1",
       "entity_type": device_type,  # RTDS
       "protocol":    "PDI-IoTA-UltraLight",
       "transport":   "MQTT",
       "timezone":    "Europe/Berlin",
       "attributes":  attributes,
       "commands":  # provisioning of actuators
       [
            {
               "name": "setpoint1",
               "type": "command",
               "value": "Number"
            },
            {
               "name": "setpoint2",
               "type": "command",
               "value": "Number"
            }
       ]
   }
]
}

d = json.dumps(d).encode('utf8')

if True:
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
    attrs.append(rtds_signals[r])

for r in np.arange(len(rtds_text)):
    attrs.append(rtds_tsignals[r])

d = {
       "description": "Notification Quantumleap: sensors from RTDS",
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
            "metadata": ["dateCreated", "dateModified"]
           },
       "throttling": 0
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker_ip, port)  # establish connection

# test_payload = ""
# for r in np.arange(len(rtds_names)):
#     rn = rtds_names[r]
#     test_payload += rn + "|" + "0.0"
#     if not r == len(rtds_names)-1:
#         test_payload += "|"
#
# print("test_payload: \n" + str(test_payload))
# print("mosquitto_pub -h "+broker_ip+" -t \"/"+api_key+"/"+device_id+"/attrs\" -m \""+test_payload+"\" ")

# ret = client1.publish("/" + api_key + "/" + device_id + "/attrs", test_payload)

time.sleep(1)

# enabling context broker commands -ACTUATORS
# "ENABLING CONTEXT BROKER COMMANDS" in tutorial https://fiware-tutorials.readthedocs.io/en/latest/iot-over-mqtt/index.html
# Once the commands have been registered it will be possible to actuate by sending requests to the Orion Context Broker,
# rather than sending UltraLight 2.0 requests directly the IoT devices.

print("\n --> 2.2. enabling context broker commands")
url = 'http://' + cloud_ip + ':1026/v2/registrations'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

d = {
      "description": "Setpoints Commands",
      "dataProvided": {
        "entities": [
          {
            "id": "Simulation:1", "type": device_type
          }
        ],
        "attrs": ["setpoint"]
      },
      "provider": {
        "http": {"url": "http://orion:1026/v1"},
        "legacyForwarding": True
      }
    }

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)
