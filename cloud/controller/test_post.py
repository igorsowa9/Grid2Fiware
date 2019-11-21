import json
import requests
import sys

fiware_service = "grid_uc"
device_type = "RTDS"
device_id = "inverter001"

device_ip = "10.12.0.10"
api_key = "asd1234rtds"

# test message: sending a value to device example
print("\n --> test patch request to device (from docker)")

value = 0.32
while True:
	url = 'http://' + device_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
	h = {
		'Content-Type': 'application/json',
		'fiware-service': fiware_service,
     		'fiware-servicepath': '/'}
	d = {
      		"setpoint": {
          	"type": "command",
          	"value": value}
    	}
	d = json.dumps(d).encode('utf8')
	response = requests.patch(url, d, headers=h)
	print(response.status_code, response.reason)  # HTTP
	print(response.text)  # TEXT/HTML
	value = value + 1
	break

