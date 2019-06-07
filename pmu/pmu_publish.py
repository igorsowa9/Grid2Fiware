import paho.mqtt.client

import urllib.request
import urllib.parse
import sys
import json
import requests
import time

# GET
# cloud_ip = "10.12.0.10"
# contents = urllib.request.urlopen("http://"+cloud_ip+":4041/iot/about").read() ## GET request
# print(contents)

# POST
url = 'http://10.12.0.10:1026/v2/entities'
d = {
    "id": "urn:ngsi-ld:Store:001",
    "type": "Store",
    "address": {
        "type": "PostalAddress",
        "value": {
            "streetAddress": "Bornholmer Straße 65",
            "addressRegion": "Berlin",
            "addressLocality": "Prenzlauer Berg",
            "postalCode": "10439"
        }
    },
    "location": {
        "type": "geo:json",
        "value": {
             "type": "Point",
             "coordinates": [13.3986, 52.5547]
        }
    },
    "name": {
        "type": "Text",
        "value": "Bösebrücke Einkauf"
    }
}

h = {'Content-Type': 'application/json'}

# d = json.dumps(d).encode('utf8')
# response = requests.post(url, data=d, headers=h)

n = 0
id = "test8_id_"

start = time.time()

while n < 10:
    idi = id + str(n)
    di = d
    di['id'] = idi
    di = json.dumps(di).encode('utf8')
    response = requests.post(url, data=di, headers=h)
    print(response.text)  # TEXT/HTML
    print(response.status_code, response.reason)  # HTTP
    n = n+1
    # time.sleep(0.01)

end = time.time()
print(end - start)


