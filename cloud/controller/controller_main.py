import json
import requests
import sys
import time
import numpy as np
from datetime import datetime
import multiprocessing
from controller_config import *

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


def pdc_newest():
    while True:
        # Get the data (through QL API but it could be also SQL request)
        url = 'http://' + cloud_ip + ':4200/_sql'
        h = {'Content-Type': 'application/json',
             'fiware-service': fiware_service,
             'fiware-servicepath': '/'}

        # now = datetime.utcnow().timestamp()
        # ts_down_ms = np.round(now*1000)-1000
        # ts_up_ms = np.round(now*1000)+1000
        # d = {"stmt":"SELECT * FROM mtgrid_uc.etrtds1 WHERE ts_measurement > "+str(int(np.round(ts_down_ms)))+" AND ts_measurement < "+str(int(np.round(ts_up_ms)))+" ORDER BY ts_measurement DESC"}

        # # Alternatively download of data through API of fiware
        # url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/ts_measurement?lastN=1'
        # h = {
        #     'Accept': 'application/json',
        #     'fiware-service': fiware_service,
        #     'fiware-servicepath': '/'
        # }
        # response = requests.get(url, headers=h)
        # parsed = json.loads(response.text)
        # print(parsed)
        # continue

        strg = ""
        n_sig = len(ras)
        for si in range(n_sig):
            strg = strg + ras[si]
            if not si == n_sig-1:
                strg = strg + ", "

        d = {"stmt": "SELECT "+strg+" FROM mtgrid_uc.etrtds1 ORDER BY ts_measurement DESC LIMIT 1"}
        d = json.dumps(d).encode('utf8')
        response = requests.post(url, data=d, headers=h)

        # print(response.status_code, response.reason)  # HTTP
        # print(response.text)  # TEXT/HTML
        parsed = json.loads(response.text)

        global meas_set
        meas_set = np.array(parsed['rows'][0])
        ts_measurement = meas_set[ras == "ts_measurement"][0]
        # print(ts_measurement)
        delay = datetime.utcnow().timestamp()*1000 - float(ts_measurement)
        print("\ndelay (measurement ("+str(ts_measurement)+") -> pdc): " + str(np.round(delay/1000, 3)) + " s")


def shedding_detector():
    # Detector for simple secondary shedding actions in case of serious deviations.
    global f1_alert, f2_alert, f3_alert, v_alert, setpoints

    if (float(meas_set[ras == "f_v3a"][0]) < f_constr1[0] or float(meas_set[ras == "f_v3a"][0]) > f_constr1[1]) and np.abs(float(meas_set[ras == "rocof_v3a"][0])) > rocof_abs_constr:
        f1_alert = 1
        setpoints[BR1] = 0.0  # 1. stage shedding
        send_setpoints(meas_set[ras == "ts_measurement"][0])
    # other stages of shedding not considered for now

    if any(x == 1 for x in [f1_alert, f2_alert, f3_alert]):
        # raise frequency alert
        pass

    if any(x < v_constr[0] for x in meas_set[4:9]) or any(x > v_constr[1] for x in meas_set[4:9]):
        v_alert = 1


def sc_continous():
    # Continous operation of the secondary controller with continous setpoints for DG in normal secondary control
    pass


def send_setpoints(ts):
    d = {}
    for rc in range(len(rtds_commands)):
        d.update({rtds_commands[rc]: {
            "type": "command",
            "value": str(setpoints[rc])
        }})
    d = json.dumps(d).encode('utf8')
    requests.patch(url, d, headers=h)

    if False:
        response = requests.patch(url, d, headers=h)
        print(response.status_code, response.reason)  # HTTP
        print(response.text)  # TEXT/HTML

        # print("SCS Implemented! Delay measurement ("+str(ts_ms)+") -> control implementation: " + str(np.round(delay/1000, 3)) + " s")
        print(np.round(delay / 1000, 3))
    delay = datetime.utcnow().timestamp() * 1000 - float(ts)
    print("Setpoints sent: delay: " + str(np.round(delay / 1000, 3)) + " s (between measurement and control setpoints "
                                                                       "derivation")
    # time.sleep(0.01)


if __name__ == '__main__':

    ras = np.concatenate((rtds_signals, rtds_tsignals))
    # Variables for live update:
    meas_set = np.zeros(len(ras))
    f1_alert = 0
    f2_alert = 0
    f3_alert = 0
    v_alert = 0

    setpoints = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # see config for what is what

    # message to RTDS:
    url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
    h = {'Content-Type': 'application/json',
         'fiware-service': fiware_service,
         'fiware-servicepath': '/'}

    p1 = multiprocessing.Process(target=pdc_newest)
    p1.start()
    p12 = multiprocessing.Process(target=pdc_newest)
    p12.start()
    # p2 = multiprocessing.Process(target=sc_continous)
    # p2.start()
    # p3 = multiprocessing.Process(target=shedding_detector)
    # p3.start()

    p1.join()
    p12.join()
    # p2.join()
    # p3.join()


