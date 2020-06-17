import json
import requests
import sys
import time
import numpy as np
from datetime import datetime
import multiprocessing
from controller_config import *
import paho.mqtt.client as paho

# parallel processes of cloud controller operation:
# PDC,
# Event detection,
# Controller (at trigger from detection).

# PDC receives the phasors and synchronizes them. It's necessary due to of loss of synchrophasor data due to arrivals and dropouts etc.
# It buffers the arriving data to choose only those from required moment.
# It should be synchronized to GPS like the meters and set it's operational frequency with max delay.

# It can reconstruct the missing data as follows:
#  - at 0 time it is inicialized with nominal values of measurement nodes
#  - Missing Amplitude and phase angle are replaced by last received samples.
#  - Missing frequency and ROCOF are interpolated based on maximum likelihood value or arithmetic mean of the available samples.
# In other words recursive behaviour in terms of local parameter (V, angle) and interpolative for the global paramenters (f, rocof).
# Recursive behaviour also in case no samples come for the required time stamp.


ran = np.concatenate((rtds_names, rtds_text))
ras = np.concatenate((rtds_signals, rtds_tsignals))

# Variables for live update:
f1_alert = 0
f2_alert = 0
f3_alert = 0
v_alert = 0

meas_set = multiprocessing.Manager().list(np.zeros(len(ras)).tolist())  # measurements from RTDS and PMU to update

# Setpoints updated by different modules and sent to devices (VM). See config for what is what
setpoints = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# message to RTDS:
url = 'http://' + cloud_ip + ':1026/v2/entities/Simulation:1/attrs?type=' + device_type
h = {'Content-Type': 'application/json',
     'fiware-service': fiware_service,
     'fiware-servicepath': '/'}


def on_connect_rtds(client, userdata, flags, rc):
    print("Connected (RTDS) with result code "+str(rc))
    client.subscribe(rtds_topic)


def on_connect_pmu(client, userdata, flags, rc):
    print("Connected (PMU) with result code "+str(rc))
    client.subscribe(pmu_topic)


def on_message_rtds(client, userdata, msg):
    # print("Topic: " + msg.topic+" Payload: "+str(msg.payload))

    entire_str = msg.payload.decode("utf-8")
    for ri in range(len(ran)):
        if not ri == len(ran)-1:
            val = find_between(str(entire_str+"|end"), ran[ri]+"|", "|"+ran[ri+1])
        else:
            val = find_between(str(entire_str + "|end"), ran[ri] + "|", "|end")
        try:
            meas_set[np.argwhere(ras == ras[ri])[0][0]] = val
        except ValueError:
            meas_set[np.argwhere(ras == ras[ri])[0][0]] = 0

    ts_measurement = meas_set[np.argwhere(ras == "ts_measurement")[0][0]]
    delay = datetime.utcnow().timestamp() * 1000 - float(ts_measurement)
    print("\nNew RTDS measurement: delay " + str(np.round(delay / 1000, 3)) + "s (measurement (" + str(ts_measurement) + ") to PDC of controller). ")

    return


def on_message_pmu(client, userdata, msg):
    entire_str = msg.payload.decode("utf-8")
    pass


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def mqtt_loop():
    """ Subscribes to the devices directly instead of obtaining data from DB."""

    # while True:
    #     meas_set[0] = 1

    client_rtds = paho.Client()
    # client_pmu = paho.Client()

    client_rtds.on_connect = on_connect_rtds
    # client_pmu.on_connect = on_connect_pmu

    client_rtds.on_message = on_message_rtds
    # client_pmu.on_message = on_message_pmu

    client_rtds.connect("10.12.0.10", 1883, 60)
    # client_pmu.connect("10.12.0.10", 1883, 60)

    print('two mqtt loops: starting')
    client_rtds.loop_forever()


def pdc_fromDB(mode):
    """Phasor data concentrator synchronizing data from different sources in the controller"""
    while True:
        # Get the data (through QL API but it could be also SQL request)
        now = datetime.utcnow().timestamp()

        if mode == 1:

            ts_down_ms = np.round(now*1000)-1000
            ts_up_ms = np.round(now*1000)+1000
            d = {"stmt":"SELECT * FROM mtgrid_uc.etrtds1 WHERE ts_measurement > "+str(int(np.round(ts_down_ms)))+" AND ts_measurement < "+str(int(np.round(ts_up_ms)))+" ORDER BY ts_measurement DESC"}

            # Alternatively download of data through API of fiware
            url = 'http://' + cloud_ip + ':8668/v2/entities/Simulation:1/attrs/ts_measurement?lastN=1'
            h = {
                'Accept': 'application/json',
                'fiware-service': fiware_service,
                'fiware-servicepath': '/'
            }
            response = requests.get(url, headers=h)
            parsed = json.loads(response.text)
            ts_measurement = 0

        if mode == 2:
            url = 'http://' + cloud_ip + ':4200/_sql'
            h = {'Content-Type': 'application/json',
                 'fiware-service': fiware_service,
                 'fiware-servicepath': '/'}
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

            meas_set = np.array(parsed['rows'][0])
            ts_measurement = meas_set[ras == "ts_measurement"][0]

        delay = now*1000 - float(ts_measurement)
        print("\ndelay (measurement ("+str(ts_measurement)+") -> pdc): " + str(np.round(delay/1000, 3)) + " s")


def shedding_detector():
    """Detector for secondary shedding actions in case of violated limits.
    Runs in parallel to reading meters."""

    global f1_alert, f2_alert, f3_alert, v_alert, setpoints

    while True:
        if (float(meas_set[np.argwhere(ras == "f_v3a")[0][0]]) < f_constr1[0]
            or float(meas_set[np.argwhere(ras == "f_v3a")[0][0]]) > f_constr1[1]) \
                and np.abs(float(meas_set[np.argwhere(ras == "rocof_v3a")[0][0]])) > rocof_abs_constr:
            f1_alert = 1
            setpoints[BR1] = 0.0  # 1. stage shedding
            send_setpoints(meas_set[np.argwhere(ras == "ts_measurement")[0][0]])
            shedding_restoration(BR1, meas_set[np.argwhere(ras == "ts_measurement")[0][0]])

        # if any(x == 1 for x in [f1_alert, f2_alert, f3_alert]):
        #     print("A (1,2 or 3) frequency alert")
        #     time.sleep(5)
        #     print("Restoration.")


def shedding_restoration(br_idx, ts):
    """Restores breaker operation after restoration_delay seconds"""
    time.sleep(restoration_delay)
    print("Restoration after "+str(restoration_delay)+" seconds.")
    setpoints[br_idx] = 1.0
    send_setpoints(ts, "SHEDDING")
    pass


def sc_continous():
    """ Continous operation of the secondary controller with continous setpoints for DG in normal secondary control
    Under development."""
    global setpoints
    while True:
        setpoints[3:] = [x * 5 for x in setpoints[3:]]
        send_setpoints(meas_set[np.argwhere(ras == "ts_measurement")[0][0]], "continous")
        # time.sleep(0.001)


def send_setpoints(ts, description):
    """ Sends setpoints to the devices. It can be called by different modules of controller."""
    d = {}
    for rc in range(len(rtds_commands)):
        d.update({rtds_commands[rc]: {
            "type": "command",
            "value": str(setpoints[rc])
        }})
    d = json.dumps(d).encode('utf8')
    response = requests.patch(url, d, headers=h)

    if False:
        response = requests.patch(url, d, headers=h)
        print(response.status_code, response.reason)  # HTTP
        print(response.text)  # TEXT/HTML

        # print("SCS Implemented! Delay measurement ("+str(ts_ms)+") -> control implementation: " + str(np.round(delay/1000, 3)) + " s")
        print(np.round(delay / 1000, 3))

    delay = datetime.utcnow().timestamp() * 1000 - float(ts)
    if str(response.status_code) == "204":
        print("Setpoints sent ("+str(description)+") with delay: " + str(np.round(delay / 1000, 3)) + " s (from measurement ts)")

def main():
    """ Runs parallel processes of the controller (secondary control):
    (i) data download from DB/ from devices,
    (ii) continous PQ control for f and V control,
    (iii) descrete actions of controller, e.g. load shedding for frequency control"""
    if not data_fromDB:
        p1 = multiprocessing.Process(target=mqtt_loop)  # subscribe directly from MQTT Broker instead of from DB
        p1.start()
    else:
        p1 = multiprocessing.Process(target=pdc_fromDB(2))  # subscribe from DB, two modes
        p1.start()

    p2 = multiprocessing.Process(target=sc_continous)
    p2.start()
    p3 = multiprocessing.Process(target=shedding_detector)
    p3.start()

    p1.join()
    p2.join()
    p3.join()


if __name__ == "__main__":
    main()
