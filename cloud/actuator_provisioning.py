import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "inverter001"

device_ip = "10.12.0.10"
api_key = "asd1234rtds"

# test message: sending a value to device example
if True:
    print("\n --> test patch request to device")
    url = 'http://' + device_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}
    d = {
          "setpoint": {
              "type": "command",
              "value": "16.33"
          }
        }
    d = json.dumps(d).encode('utf8')
    response = requests.patch(url, d, headers=h)
    print(response.status_code, response.reason)  # HTTP
    print(response.text)  # TEXT/HTML
    sys.exit()

# query data over ID from OrionCB - i.e. when i need to take measurements to the controller
if False:
    print("\n --> query data over ID from OrionCB:")
    url = 'http://' + device_ip + ':1026/v2/entities'#/Simulation:1'
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}
    response = requests.get(url)
    print(response.status_code, response.reason)  # HTTP
    print(response.text)  # TEXT/HTML
    sys.exit()

# 2. provisioning a service group for actuators - exactly the same as in the sensors

# 3. provisioning an actuator
print("\n --> 2.1. provisioning an actuator")

url = 'http://' + device_ip + ':4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

d = {
"devices":
        [
           {
             "device_id": device_id,  # (this will be your topic fort he subscriber)
             "entity_name": "Simulation:1",
             "entity_type": device_type,
             "protocol": "PDI-IoTA-JSON",  # (or PDI-IoTA-Ultralight  )PDI-IoTA-JSON
             "transport": "MQTT",
             "timezone": "Europe/Berlin",
             "commands":
             [
                {
                    "name": "setpoint",
                    "type": "command",
                    "value": "Number"
                }
             ]
           }
        ]
    }

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# enabling context broker commands
# "ENABLING CONTEXT BROKER COMMANDS" in tutorial https://fiware-tutorials.readthedocs.io/en/latest/iot-over-mqtt/index.html
# Once the commands have been registered it will be possible to actuate by sending requests to the Orion Context Broker,
# rather than sending UltraLight 2.0 requests directly the IoT devices.

print("\n --> 2.2. enabling context broker commands")
url = 'http://' + device_ip + ':1026/v2/registrations'
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
