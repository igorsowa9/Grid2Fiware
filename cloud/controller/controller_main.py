import json
import requests
import sys
import time
import numpy as np
from datetime import datetime

fiware_service = "grid_uc"
device_type = "rtds1"

cloud_ip = "10.12.0.10"
api_key = "asd1234rtds"

rtds_commands = np.array(["sc_brk1", "sc_brk2", "sc_brk3", "sc_brk4", "sc_brk5", "sc_brk6"])

# parallel proceses: PDC, detection and controller (at trigger from detection).

# PDC receives the phasors and synchronizes them.
# Because of loss of synchrophasor data due to arrivals and dropouts etc.
# "Buffers" the arriving data to choose only those from required moment
# It can reconstruct the missing data as follows:
# at 0 time it is inicilized with nominal values of measurement nodes
# Missing Amplitude and phase angle are replaced by last received samples.
# Missing frequency and ROCOF are interpolated based on maximum likelihood value or arithmetic mean of the available
# samples.
# In other words: recursive behaviour in terms of local parameter (V, angle) and interpolative for the global
# paramenters (f, rocof).
# Recursive behaviour if none of samples come for the required time stamp.

meas_set = np.array([])
f_alert = 0
v_alert = 0

def pdc():
    # Get the data (through QL API but it could be also SQL request)
    url = 'http://' + cloud_ip + ':4200/_sql'
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}

    # now = datetime.utcnow().timestamp()
    # ts_down_ms = np.round(now*1000)-1000
    # ts_up_ms = np.round(now*1000)+1000
    # d = {"stmt":"SELECT * FROM mtgrid_uc.etrtds1 WHERE ts_measurement > "+str(int(np.round(ts_down_ms)))+" AND ts_measurement < "+str(int(np.round(ts_up_ms)))+" ORDER BY ts_measurement DESC"}
    d = {"stmt": "SELECT * FROM mtgrid_uc.etrtds1 ORDER BY ts_measurement DESC LIMIT 1"}
    d = json.dumps(d).encode('utf8')
    response = requests.post(url, data=d, headers=h)

    # print(response.status_code, response.reason)  # HTTP
    print(response.text)  # TEXT/HTML

    parsed = json.loads(response.text)
    # print(parsed['rows'])

    ts_measurement = parsed['rows'][0][7]
    delay = datetime.utcnow().timestamp()*1000 - float(ts_measurement)
    print("delay (measurement -> pdc): " + str(np.round(delay/1000, 3)) + " s")
    global meas_set

    meas_set = [parsed['rows'][0][7],  # ts in ms
                parsed['rows'][0][13],  # w1
                parsed['rows'][0][2],  # f_vc1a
                parsed['rows'][0][5],  # rocof_vc1a
                parsed['rows'][0][9],  # vc1rms
                parsed['rows'][0][11],  # vo1rms
                parsed['rows'][0][10],  # vc2rms
                parsed['rows'][0][12],  # vo2rms
                parsed['rows'][0][8]]  # v3rms
    return

    # Alternative download of data through API of fiware
    # url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/w1?lastN=1'
    # h = {
    #     'Accept': 'application/json',
    #     'fiware-service': fiware_service,
    #     'fiware-servicepath': '/'
    # }
    # response = requests.get(url, headers=h)
    # parsed = json.loads(response.text)


def scs(ts_ms):
    # disconnects part of the load
    # 3. send the data to the device/VM-RTDS

    # print("\n --> Patch setpoints to device")
    url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}

    d = {}
    comm = [1.0, 1.0, 0.0, 1.0, 1.0, 1.0]
    for rc in range(len(rtds_commands)):
        d.update({rtds_commands[rc]: {
            "type": "command",
            "value": str(comm[rc])
            }})
    # d = {
    #     "setpoint1": {
    #         "type": "command",
    #         "value": str(2113)
    #     },
    #     "setpoint2": {
    #         "type": "command",
    #         "value": str(12)
    #     }
    # }
    d = json.dumps(d).encode('utf8')
    response = requests.patch(url, d, headers=h)
    # print(response.status_code, response.reason)  # HTTP
    # print(response.text)  # TEXT/HTML
    delay = datetime.utcnow().timestamp()*1000 - float(ts_ms)
    print("SCS Implemented! Delay measurement -> control implementation: " + str(np.round(delay/1000, 3)) + " s")
    global f_alert
    global v_alert
    f_alert = 0
    v_alert = 0
    # time.sleep(0.01)


while True:
    pdc()  # should be in parallel?
    # 1. detector if the secondary action have to be triggered:
    f_constr = np.array([47.0, 53.0])
    rocof_abs_constr = 1.5
    v_constr = np.array([0.190, 0.270])

    # print(meas_set)
    if (meas_set[2] < f_constr[0] or meas_set[2] > f_constr[1]) and np.abs(meas_set[3]) > rocof_abs_constr:
        f_alert = 1
    if any(x < v_constr[0] for x in meas_set[4:9]) or any(x > v_constr[1] for x in meas_set[4:9]):
        v_alert = 1

    print("alerts: f:" + str(f_alert) + " v:" + str(v_alert))
    if any(x == 1 for x in [v_alert, f_alert]):
        scs(meas_set[0])

    # if meas_set[4:8]



