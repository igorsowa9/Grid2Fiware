import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys

fiware_service = "grid_uc"  # only with different fiware_service, the actuators works with sensors
device_type = "RTDS"
# device_id = "inverter001"

cloud_ip = "10.12.0.10"
api_key_actuators = "asd1234rtds"

# test message: sending a value to device example
if True:
    print("\n --> test patch request to device")
    url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}
    d = {
            "setpoint1": {
                "type": "command",
                "value": "0.11"
            },
            "setpoint2": {
                "type": "command",
                "value": "0.22"
            }
        }
    d = json.dumps(d).encode('utf8')
    response = requests.patch(url, d, headers=h)
    print(response.status_code, response.reason)  # HTTP
    print(response.text)  # TEXT/HTML
    sys.exit()

# query data over ID from OrionCB - i.e. when i need to take measurements to the controller
if True:
    print("\n --> query data over ID from OrionCB:")
    # url = 'http://' + device_ip + ':1026/v2/'#entities'#/Simulation:1'
    url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1'
    h = {'fiware-service': fiware_service,
         'fiware-servicepath': '/'}
    response = requests.get(url, headers=h)
    print(response.status_code, response.reason)  # HTTP
    print(response.text)  # TEXT/HTML
    sys.exit()

# 2. provisioning a service group for actuators - api key changed
print("\n --> 2. provisioning a service group for mqtt actuators")

url = 'http://' + cloud_ip + ':4041/iot/services'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}
d = {
    "services": [
       {
           "apikey": api_key_actuators,
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


# 3. provisioning an actuator
print("\n --> 2.1. provisioning an actuator")

url = 'http://' + cloud_ip + ':4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}

d = {
"devices":
        [
           {
             "device_id": device_id,  # (this will be your topic fort he subscriber) rtds001
             "entity_name": "Simulation:1",
             "entity_type": device_type,  # RTDS
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
