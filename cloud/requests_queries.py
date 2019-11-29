import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np
import sys
import timeit

fiware_service = "grid_uc"  # only with different fiware_service, the actuators works with sensors
device_type = "RTDS"
# device_id = "inverter001"

cloud_ip = "10.12.0.10"
api_key_actuators = "asd1234rtds"

# test message: sending a value to device example
if False:
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
def get_measurements_GET(): #  3-5 sec / query
    # print("\n --> query data over ID from OrionCB:")
    # url = 'http://' + device_ip + ':1026/v2/'#entities'#/Simulation:1'
    url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1'
    h = {'fiware-service': fiware_service,
         'fiware-servicepath': '/'}
    response = requests.get(url, headers=h)
    # print(response.status_code, response.reason)  # HTTP
    # print(response.text)  # TEXT/HTML


def get_measurements_get_ql():  # ~163ms / query
    # print("\n --> query data from QL:")
    url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/p2meas?lastN=1'
    h = {   'Accept': 'application/json',
            'fiware-service': fiware_service,
            'fiware-servicepath': '/'}
    response = requests.get(url, headers=h)
    # print(response.status_code, response.reason)  # HTTP
    # print(response.text)  # TEXT/HTML


# query to crate
def get_measurements_sql():  # ~91ms / query
    # print("\n --> query to crate")
    # url = 'http://' + device_ip + ':1026/v2/'#entities'#/Simulation:1'
    url = 'http://' + cloud_ip + ':4200/_sql'
    h = {   'Content-Type': 'application/json'
            # 'fiware-service': fiware_service,
            # 'fiware-servicepath': '/'
        }
    d = {"stmt": "SELECT * FROM mtgrid_uc.etrtds LIMIT 10;"}
    d = json.dumps(d).encode('utf8')
    response = requests.post(url, data=d, headers=h)
    # print(response.status_code, response.reason)  # HTTP
    # print(response.text)  # TEXT/HTML


print(timeit.timeit(get_measurements_get_ql, number=100)/100)
sys.exit()


############################

# 3. provisioning an actuator ONLY - makes mess
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

