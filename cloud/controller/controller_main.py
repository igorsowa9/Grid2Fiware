import json
import requests
import sys
import time

fiware_service = "grid_uc"
device_type = "RTDS"

cloud_ip = "10.12.0.10"
api_key = "asd1234rtds"

while True:

	# Get the data through QL:
	url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/p2meas?lastN=1'
	h = {
		'Accept': 'application/json',
		'fiware-service': fiware_service,
		'fiware-servicepath': '/'
	}
	response = requests.get(url, headers=h)
	# print(response.status_code, response.reason)  # HTTP
	parsed = json.loads(response.text)
	P2meas = float(parsed['data']['values'][0])  # loads measurements

	url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/q2meas?lastN=1'
	response = requests.get(url, headers=h)
	parsed = json.loads(response.text)
	Q2meas = float(parsed['data']['values'][0])  # loads measurements

	# print(P2meas)
	# print(Q2meas)

	# 2. calculate the control settings:
	P2set = -1*P2meas
	Q2set = -1*Q2meas
	# print(P2set)
	# print(Q2set)

	# 3. send the data to the device/VM-RTDS

	print("\n --> Patch setpoints to device")
	url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
	h = {'Content-Type': 'application/json',
		 'fiware-service': fiware_service,
		 'fiware-servicepath': '/'}
	d = {
		"setpoint1": {
			"type": "command",
			"value": str(P2set)
		},
		"setpoint2": {
			"type": "command",
			"value": str(Q2set)
		}
	}
	d = json.dumps(d).encode('utf8')
	response = requests.patch(url, d, headers=h)
	print(response.status_code, response.reason)  # HTTP
	print(response.text)  # TEXT/HTML

	time.sleep(0.5)



