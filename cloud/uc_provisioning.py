import json
import requests
import time
import paho.mqtt.client as paho
import numpy as np

devices = np.array(["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8"])
fiware_service = "grid_uc"

broker = "10.12.0.10"
port = 1883


def on_publish(client,userdata,result):             #create function for callback
    print("My data published! \n")
    pass


client1 = paho.Client("control1")  # create client object
client1.on_publish = on_publish  # assign function to callback
client1.connect(broker, port)  # establish connection


# 1. pushing the model
print("\n --> 1. data model")

url = 'http://10.12.0.10:1026/v2/entities'
h = {'Content-Type': 'application/json',
     'fiware-service': ''+ fiware_service + '',
     'fiware-servicepath': '/'}

d = {
        "id": "Simulation:1",
        "type": "pmu",
        "slackP": {
          "value": 17.23
        },
        "pQLoadProfileP": {
          "value": 1.23
        },
        "solarGeneratorP": {
          "value": 1.23
        },
        "SimTime": {
          "value": 0
        }
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# 2. provisioning a service group for mqtt
print("\n --> 2. provisioning a service group for mqtt")

url = 'http://10.12.0.10:4041/iot/services'
h = {'Content-Type': 'application/json',
     'fiware-service': 'fmu',
     'fiware-servicepath': '/'}
d = {
    "services": [
       {
           "apikey": "1234",
           "cbroker": "http://orion:1026",
           "entity_type": "FMU",
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

url = 'http://10.12.0.10:4041/iot/devices'
h = {'Content-Type': 'application/json',
     'fiware-service': 'fmu',
     'fiware-servicepath': '/'}
d = {
"devices": [
   {
     "device_id":   "fmu",
     "entity_name": "Simulation:1",
     "entity_type": "FMU",
     "protocol":    "PDI-IoTA-UltraLight",
     "transport":   "MQTT",
     "timezone":    "Europe/Berlin",
     "attributes": [
       { "object_id": "sp", "name": "slackP", "type": "Number" },
       { "object_id": "pqp", "name": "pQLoadProfileP", "type": "Number" },
       { "object_id": "sgp", "name": "solarGeneratorP", "type": "Number" },
       { "object_id": "st", "name": "SimTime", "type": "Number" }
    ]
   }
]
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

time.sleep(1)

# 4. making subscriptions of QL
print("\n --> 4. making subscriptions of QL")

url = 'http://10.12.0.10:1026/v2/subscriptions/'
h = {'Content-Type': 'application/json',
     'fiware-service': 'fmu',
     'fiware-servicepath': '/'}
d = {
       "description": "Notification Quantumleap",
       "subject": {
           "entities": [
               {"id": "Simulation:1", "type": "FMU"}
           ],
           "condition": {
               "attrs": [
                   "slackP",
                   "pQLoadProfileP",
                   "solarGeneratorP",
                   "SimTime"
               ]
           }
               },
           "notification": {
                "http": {"url": "http://quantumleap:8668/v2/notify"},
                "attrs": [
                   "slackP",
                   "pQLoadProfileP",
                   "solarGeneratorP",
                   "SimTime"
               ],
            "metadata": ["dateCreated", "dateModifid"]
           },
       "throttling": 0
}

d = json.dumps(d).encode('utf8')
response = requests.post(url, data=d, headers=h)

print(response.status_code, response.reason)  # HTTP
print(response.text)  # TEXT/HTML

ret = client1.publish("/1234/fmu/attrs", "sp|1|pqp|1|sgp|1|st|1")
