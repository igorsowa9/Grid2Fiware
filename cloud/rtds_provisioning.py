import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys
from settings import *

n_pmu_analog_channels = 8  # determined by number of chanells in DAQ
n_pmu_streams_to_cloud = 40  # 8x5 from each channel with have magn, ang, freq, rocof, time, ... (?)

# rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4", "rtds5", "rtds6", "rtds7"])
# rtds_text = np.array(["ts1", "add1"])
#
# rtds_signals = np.array(["w3", "f_v3a", "rocof_v3a", "vo1llrms", "vo2llrms", "vo3llrms", "vo4llrms"])
# rtds_tsignals = np.array(["ts_measurement", "notes"])
#
# rtds_commands = np.array(["sc_brk1", "sc_brk2", "sc_brk3", "pref1", "pref2", "pref3", "pref4", "qref1", "qref2", "qref3", "qref4"])

fiware_service = "grid_uc"
device_type = "rtds1"
device_id = "rtds001"

cloud_ip = "10.12.0.10"
# cloud_ip = "127.0.0.1"
broker_ip = cloud_ip
port = 1883
api_key = "asd1234rtds"

def on_publish(client,userdata,result):             #create function for callback
    print("My data published! \n")
    pass

## provisioning communication: device(mqtt)-though MQTT Broker and Orion- to Quantum Leap + Crate DB + Grafana
print("\n Provisioning communication:"
      "\n\t\t - RTDS measurements to FIWARE"
      "\n\t\t - Controller (in FIWARE) control settings to RTDS acutators")

# 1. push data model
print("\n--> 1. Provisioning RTDS data model.")

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
print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML

time.sleep(1)

# 2. provisioning a service group for mqtt
print("\n--> 2. Provisioning service groups for MQTT.")

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

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML

time.sleep(1)

# 3. provisioning sensors and actuatros
print("\n--> 3. Provisioning sensors and actuators devices.")

url = 'http://' + cloud_ip + ':4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

attributes = []

for ch in np.arange(len(rtds_names)):
    attributes.append({"object_id": rtds_names[ch], "name": rtds_signals[ch], "type": "Number"})

for ch in np.arange(len(rtds_text)):
    attributes.append({"object_id": rtds_text[ch], "name": rtds_tsignals[ch], "type": "Text"})
# print(attributes)

commands = []
for ch in np.arange(len(rtds_commands)):
    commands.append({"name": rtds_commands[ch], "type": "command", "value": "Number"})
# commands.append({"name": rtds_commands_attch[0], "type": "command", "value": "Number"})
# print(commands)
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
       "commands":  commands  # provisioning of actuators
   }
]
}

d = json.dumps(d).encode('utf8')

if True:
    response = requests.post(url, data=d, headers=h)
    print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML
    time.sleep(1)

# 4. making subscriptions of QL
print("\n--> 4. making subscriptions of QL.")

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

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML

client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker_ip, port)  # establish connection
time.sleep(1)

# enabling context broker commands for actuators
# See: https://fiware-tutorials.readthedocs.io/en/latest/iot-over-mqtt/index.html

print("\n--> 5. Enabling context broker commands.")
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

print(response.status_code, response.reason, " -- ", response.text)  # HTTP # TEXT/HTML

time.sleep(1)
