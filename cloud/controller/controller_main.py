import json
import requests
import sys
import time
import numpy as np
from datetime import datetime
import multiprocessing
from controller_config import *
import paho.mqtt.client as paho
import itertools
import pandas as pd

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


ran = np.concatenate((rtds_names, rtds_text)).tolist()
ras = np.concatenate((rtds_signals, rtds_tsignals)).tolist()

pan = [0]*(len(channel_names)*len(sub_names))
pas = [0]*(len(channel_names)*len(sub_names))
for ai in range(len(channel_names)):
    a = channel_names[ai]
    a1 = channel_signals[ai]
    for bi in range(len(sub_names)):
        b = sub_names[bi]
        b1 = sub_signals[bi]
        pan[ai * len(sub_names) + bi] = str(a) + str(b)
        pas[ai * len(sub_names) + bi] = str(a1) + "_" + str(b1)

# Variables for live update:
f1_alert = 0
f2_alert = 0
f3_alert = 0
v_alert = 0

# structures with measurement values to share using Manager between the processes
meas_set_rtds = multiprocessing.Manager().list(np.zeros(len(ras)).tolist())  # measurements from RTDS to update
meas_set_pmu = multiprocessing.Manager().list(np.zeros(len(pas)).tolist())

mem_size = 5
df_rtds = pd.DataFrame(np.nan, index=list(range(mem_size)), columns=list(ras))
ns_rtds = multiprocessing.Manager().Namespace()
ns_rtds.df = df_rtds

df_pmu = pd.DataFrame(np.nan, index=list(range(mem_size)), columns=list(pas))
ns_pmu = multiprocessing.Manager().Namespace()
ns_pmu.df = df_pmu

# synchronized data for controller
meas_synch = multiprocessing.Manager().list(np.zeros(len(ras)+len(pas)+1).tolist())  # measurements from RTDS to update

# Setpoints updated by different modules and sent to devices (VM). See config for what is what
setpoints = multiprocessing.Manager().list(default_controls + [0, "description"])  # 2 last elements for ts and description

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
    global ns_rtds
    # print("Topic: " + msg.topic+" Payload: "+str(msg.payload))
    entire_str = msg.payload.decode("utf-8")
    # print("topic: " + str(msg.topic) + "\t payload:" + str(entire_str))

    for ri in range(len(ran)):
        if not ri == len(ran)-1:
            val = find_between(str(entire_str+"|end"), ran[ri]+"|", "|"+ran[ri+1])
        else:
            val = find_between(str(entire_str + "|end"), ran[ri] + "|", "|end")
        try:
            meas_set_rtds[ras.index(ras[ri])] = np.round(float(val), 3)
        except ValueError:
            meas_set_rtds[ras.index(ras[ri])] = 0

    new_row_df = pd.DataFrame(np.array(meas_set_rtds), index=list(ras)).T
    ns_rtds.df = pd.concat([new_row_df, ns_rtds.df], ignore_index=True)
    ns_rtds.df = ns_rtds.df.drop([mem_size])
    return
    # delay at measurement arrival, if necessary
    ts_measurement = meas_set_rtds[ras.index("ts_measurement")]
    delay = datetime.utcnow().timestamp() * 1000 - float(ts_measurement)  # TIMESTAMP measured --------------

    print("New RTDS measurement: delay " + str(np.round(delay / 1000, 3)) +
          "s (measurement (" + str(ts_measurement) + ") to PDC of controller). Current rtds measurements buffer: " + str(df_rtds))
    return


def on_message_pmu(client, userdata, msg):
    global ns_pmu
    entire_str = msg.payload.decode("utf-8")
    # print("topic: " + str(msg.topic) + "\t payload:" + str(entire_str))

    for ri in range(len(pan)):
        if not ri == len(pan)-1:
            val = find_between(str(entire_str+"|end"), pan[ri] + "|", "|" + pan[ri+1])
        else:
            val = find_between(str(entire_str + "|end"), pan[ri] + "|", "|end")
        try:
            meas_set_pmu[pas.index(pas[ri])] = np.round(float(val), 3)
        except ValueError:
            meas_set_pmu[pas.index(pas[ri])] = 0

    new_row_df = pd.DataFrame(np.array(meas_set_pmu), index=list(pas)).T
    ns_pmu.df = pd.concat([new_row_df, ns_pmu.df], ignore_index=True)
    ns_pmu.df = ns_pmu.df.drop([mem_size])
    return
    # delay at measurement arrival, if necessary
    ts_measurement = meas_set_pmu[pas.index("vo1a_timestamp")]
    delay = datetime.utcnow().timestamp() * 1000 - float(ts_measurement)
    print("New PMU measurement: delay " + str(np.round(delay / 1000, 3)) +
          "s (measurement (" + str(ts_measurement) + ") to PDC of controller). Current pmu measurements buffer: " + str(df_pmu))
    return


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def mqtt_loop1():
    """ Subscribes to the devices directly instead of obtaining data from DB."""
    client_rtds = paho.Client("cli1")
    client_rtds.on_connect = on_connect_rtds
    client_rtds.on_message = on_message_rtds
    client_rtds.connect("10.12.0.1")
    print('mqtt loop1: starting')
    client_rtds.loop_forever()


def mqtt_loop2():
    client_pmu = paho.Client("cli2")
    client_pmu.on_connect = on_connect_pmu
    client_pmu.subscribe(pmu_topic)
    client_pmu.on_message = on_message_pmu
    client_pmu.connect("10.12.0.6")
    print('mqtt loop2: starting')
    client_pmu.loop_forever()


def pdc_mqtt():
    """synchronization is done at the end of the period (looking back at the measurements from the period which is
    finishing. """
    global ns_rtds, ns_pmu
    squence_ms = 1000  # that often the whole sequence of synchronization run, what define a granularity of calculations
    delay_ms = 200  # that much delay can each sequence allow. After they are either approximated or copied.

    mem_rtds_latest = 0  # local single copy in case of need for approximation / average etc.
    mem_pmu_latest = 0

    time.sleep(0.3)  # wait for first measurements before running

    while True:
        now_ms = round(datetime.utcnow().timestamp() * 1000, 0)
        start_of_considered_interval = now_ms - squence_ms
        df_rtds = ns_rtds.df
        ds_pmu = ns_pmu.df

        # only measurements from now (with margin) to standard period of synchronization
        try:
            rtds_filter = df_rtds.loc[(ns_rtds.df['ts_measurement'] >= start_of_considered_interval) & (ns_rtds.df['ts_measurement'] < now_ms + delay_ms)]
            pmu_filter = ds_pmu.loc[(ns_pmu.df['vt_timestamp'] >= start_of_considered_interval) & (ns_pmu.df['vt_timestamp'] < now_ms + delay_ms)]
        except pd.core.indexing.IndexingError:
            print("Indexing Error in PDC.")

        if rtds_filter.empty:  # if selection is empty for this ts, take the previous one directly
            print("Missing RTDS data. Approximation.")
            rtds_latest = mem_rtds_latest
        else:  # choosing the latest measurements in case there are more
            rtds_latest = rtds_filter.iloc[rtds_filter['ts_measurement'].idxmax()]
        if pmu_filter.empty:
            print("Missing PMU data. Approximation.")
            pmu_latest = mem_pmu_latest
        else:
            pmu_latest = pmu_filter.iloc[pmu_filter['vt_timestamp'].idxmax()]

        # rtds_latest = rtds_filter.iloc[rtds_filter['ts_measurement'].idxmax()] if not rtds_filter.empty else 0
        # pmu_latest = pmu_filter.iloc[pmu_filter['vt_timestamp'].idxmax()] if not pmu_filter.empty else 0

        mem_rtds_latest = rtds_latest
        mem_pmu_latest = pmu_latest

        if rtds_filter.empty == False and pmu_filter.empty == False:  # if we have both "fresh" measurement set
            meas_synch[0] = now_ms
            meas_synch[1:len(ras)+1] = rtds_latest.values.tolist()
            meas_synch[len(ras)+1:] = pmu_latest.values.tolist()

        # print(meas_synch[14])
        time.sleep(0.05)


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
    Runs in parallel to reading meters and PDC and sequentially with controller, it is able to trigger it."""

    global f1_alert, f2_alert, f3_alert, v_alert
    ctr_names = ['ts_pdc'] + ras + pas
    ts_pdc_mem = 0

    while True:
        time.sleep(0.05)
        meas_synch_now = meas_synch

        if meas_synch_now[ctr_names.index("ts_pdc")] == ts_pdc_mem:  # skip if the function was already running for this timestep (regardless output)
            # print("Repeated shedding detection - ignored.")
            continue

        ts_pdc_mem = meas_synch_now[ctr_names.index("ts_pdc")]
        min_ts = min(meas_synch_now[ctr_names.index("ts_pdc")], meas_synch_now[ctr_names.index("ts_measurement")],
                     meas_synch_now[ctr_names.index("vt_timestamp")])

        print("Shed. Det.: synchronized input set (no-reps) with ts_pdc: " + str(meas_synch_now[0]) +
              " and min_ts: " + str(min_ts) + ". PDC set span: " + str(meas_synch_now[0]-min_ts))

        if (meas_synch_now[ctr_names.index("f_bus")] < f_constr1[0]
            or meas_synch_now[ctr_names.index("f_bus")] > f_constr1[1]) \
                and np.abs(meas_synch_now[ctr_names.index("rocof_bus")]) > rocof_abs_constr:
            f1_alert = 1
            setpoints[BR1] = 0.0  # 1. stage shedding
            setpoints[-2] = min_ts
            setpoints[-1] = "1. stage shedding"

            print("\tShed. Det.: delay when f detector triggers send_setpoints (relatively to min_ts): " + str(
                round(datetime.utcnow().timestamp() * 1000 - min_ts, 0)) + "ms")
            send_setpoints(min_ts, "Shedding from detector")  # with the earliest (synchronized) timestamp
            # shedding_restoration(BR1, meas_synch[ctr_names.index("ts_measurement")])

        if (meas_synch_now[ctr_names.index("f_bus")] < f_constr2[0]
            or meas_synch_now[ctr_names.index("f_bus")] > f_constr2[1]) \
                and np.abs(meas_synch_now[ctr_names.index("rocof_bus")]) > rocof_abs_constr:
            f1_alert = 1
            f2_alert = 1
            setpoints[BR1] = 0.0  # 1. stage shedding
            setpoints[BR2] = 0.0  # 2. stage shedding
            setpoints[-2] = min_ts
            setpoints[-1] = "2. stage shedding"

            print("\tShed. Det.: delay when f detector triggers send_setpoints (relatively to min_ts): " + str(
                round(datetime.utcnow().timestamp() * 1000 - min_ts, 0)) + "ms")
            send_setpoints(min_ts, "Shedding from detector")  # with the earliest (synchronized) timestamp
            # shedding_restoration(BR1, meas_synch[ctr_names.index("ts_measurement")])

        if (meas_synch_now[ctr_names.index("f_bus")] < f_constr3[0]
            or meas_synch_now[ctr_names.index("f_bus")] > f_constr3[1]) \
                 and np.abs(meas_synch_now[ctr_names.index("rocof_bus")]) > rocof_abs_constr:
            f1_alert = 1
            f2_alert = 1
            f3_alert = 1
            setpoints[BR1] = 0.0  # 1. stage shedding
            setpoints[BR2] = 0.0  # 2. stage shedding
            setpoints[BR3] = 0.0  # 3. stage shedding
            setpoints[-2] = min_ts
            setpoints[-1] = "3. stage shedding"

            print("\tShed. Det.: delay when f detector triggers send_setpoints (relatively to min_ts): " + str(round(datetime.utcnow().timestamp() * 1000 - min_ts, 0)) + "ms")
            send_setpoints(min_ts, "Shedding from detector")  # with the earliest (synchronized) timestamp
            # shedding_restoration(BR1, meas_synch[ctr_names.index("ts_measurement")])


# def shedding_restoration(br_idx, ts):
#     """Restores (closes) br_idx breaker operation after restoration_delay seconds"""
#     time.sleep(restoration_delay)
#     print("Restoration after "+str(restoration_delay)+" seconds.")
#     setpoints[br_idx] = 1.0
#     send_setpoints(ts, "Restoration of breaker with idx:" + str(br_idx))
#     pass


# def sc_continous():
#     """ Continous operation of the secondary controller with continous setpoints for DG in normal secondary control
#     Under development."""
#     ctr_names = ['ts_pdc'] + ras + pas
#     while True:
#         curr_meas_synch = meas_synch
#         curr_setpoints = setpoints
#
#         new_pq = [x + 5 for x in curr_setpoints[3:-2]]  # test setpoints
#         # update of shared setpoints
#         setpoints[3:-2] = new_pq
#         setpoints[-2] = curr_meas_synch[ctr_names.index("ts_pdc")]
#         setpoints[-1] = "Continous control"
#         print("Continues controller sets setpoints from (ts_pdc: " + str(curr_meas_synch[ctr_names.index("ts_pdc")]) + ")")
#         # send_setpoints(meas_synch[ctr_names.index("ts_pdc")], "Continous control")
#         time.sleep(1)


def send_setpoints(min_ts, description):
    """ Sends setpoints to the devices. SEtpoints can be updated by different modules of controller."""
    # time.sleep(0.5)

    curr_setpoints = setpoints

    if True:
        # time.sleep(0.00)
        d = {}
        for rc in range(len(rtds_commands)):
            d.update({rtds_commands[rc]: {
                "type": "command",
                "value": str(curr_setpoints[rc])
            }})
        # d.update({rtds_commands_attch[0]: {
        #     "type": "command",
        #     "value": "123"
        # }})
        print(d)
        d = json.dumps(d).encode('utf8')

        ts_send = round(datetime.utcnow().timestamp() * 1000, 0)
        print("\t\tSend_setp.: is about to send current setpoints (ts_send="+str(ts_send)+
              ") due to trigger: "+str(description)+". Based on measurements with min_ts=" + str(min_ts))
        response = requests.patch(url, d, headers=h)
        delay_for_patch = datetime.utcnow().timestamp() * 1000 - ts_send
        if False:
            print(response.status_code, response.reason)  # HTTP
            print(response.text)  # TEXT/HTML

        if str(response.status_code) == "204":
            print("\t\tSend_setp.: Successful patch request with setpoints gives additional delay (now-ts_send): "+str(round(delay_for_patch, 0))+"ms" )


def main():
    """ Runs parallel processes of the controller (secondary control):
    (i) data download from DB/ from devices,
    (ii) continous PQ control for f and V control,
    (iii) descrete actions of controller, e.g. load shedding for frequency control"""

    if not data_fromDB:
        p1 = multiprocessing.Process(target=mqtt_loop1)  # subscribe directly from MQTT Broker instead of from DB
        p1.start()
        p2 = multiprocessing.Process(target=mqtt_loop2)
        p2.start()
    else:
        p1 = multiprocessing.Process(target=pdc_fromDB(2))  # subscribe from DB, two modes
        p1.start()

    p3 = multiprocessing.Process(target=pdc_mqtt)
    p3.start()
    p4 = multiprocessing.Process(target=shedding_detector)
    p4.start()
    # p5 = multiprocessing.Process(target=sc_continous)
    # p5.start()
    # p6 = multiprocessing.Process(target=send_setpoints)
    # p6.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()
    # p5.join()
    # p6.join()
    return

    p4 = multiprocessing.Process(target=sc_continous)
    p4.start()


    p1.join()
    p2.join()
    p3.join()
    p4.join()


if __name__ == "__main__":
    main()
