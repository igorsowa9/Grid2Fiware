import numpy as np

fiware_service = "grid_uc"
device_type = "rtds1"

cloud_ip = "10.12.0.10"
api_key = "asd1234rtds"

rtds_names = np.array(["rtds1", "rtds2", "rtds3", "rtds4",
                       "rtds5", "rtds6", "rtds7",
                       "rtds8", "rtds9", "rtds10", "rtds11", "rtds12", "rtds13"])
rtds_text = np.array(["ts1", "add1"])
rtds_signals = np.array(["w_bus", "f_bus", "rocof_bus", "v_bus",
                         "vo1llrms", "vo2llrms", "vo3llrms",
                         "Po1", "Qo1", "Po2", "Qo2", "Po3", "Qo3"])
rtds_tsignals = np.array(["ts_measurement", "notes"])
NumData_fromRTDS = 13

default_controls = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
rtds_commands = np.array(["sc_brk1", "sc_brk2", "sc_brk3",
                          "pref1", "pref2", "pref3",
                          "qref1", "qref2", "qref3"])

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
Q1 = 6
Q2 = 7
Q3 = 8

restoration_delay = 5  # seconds for restoration of basic operation after shedding