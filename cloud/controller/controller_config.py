import numpy as np

fiware_service = "grid_uc"
device_type = "rtds1"

cloud_ip = "10.12.0.10"
api_key = "asd1234rtds"

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4", "rtds5", "rtds6", "rtds7"])
rtds_text = np.array(["ts1", "add1"])

rtds_signals = np.array(["w3", "f_v3a", "rocof_v3a", "vo1llrms", "vo2llrms", "vo3llrms", "vo4llrms"])
rtds_tsignals = np.array(["ts_measurement", "notes"])

rtds_commands = np.array(["sc_brk1", "sc_brk2", "sc_brk3", "pref1", "pref2", "pref3", "pref4", "qref1", "qref2", "qref3", "qref4"])

# subscription of data from RTDS and PMU (directly, not through CrateDB)
rtds_topic = "/asd1234rtds/rtds001/attrs"
pmu_topic = ""

data_fromDB = False  # data from controller either from DB (True) or directly through MQTT subscription from meters


# settings for shedding:
f_constr1 = np.array([49.0, 51.0])
f_constr2 = np.array([46.0, 54.0])
f_constr3 = np.array([45.0, 55.0])
rocof_abs_constr = 1.5
v_constr = np.array([0.190, 0.270])

# message from controller, indexes of setpoints:
BR1 = 0
BR2 = 1
BR3 = 2
P1 = 3
P2 = 4
P3 = 5
P4 = 6
Q1 = 7
Q2 = 8
Q3 = 9
Q4 = 10

restoration_delay = 5  # seconds