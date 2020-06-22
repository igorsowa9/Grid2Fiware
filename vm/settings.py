import platform, sys
import numpy as np

#if str(platform.machine())=='x86_64':
#    IPinput = input("input your IP (leave empty for previous one): ")
#    if IPinput == "":
#        IPinput = '137.226.124.77'
#else: IPinput = '134.130.169.61' # for raspberry

IP_send = '134.130.169.96'  # of GTNET, not rack, not own IP
IP_receive = '134.130.169.12'  # should be updated by the current public (depending on configuration) IP address?
Port_send = 12334
Port_receive = 12334

# RTDS
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
rtds_commands_attch = ['min_ts']

# PMU
channel_names = np.array(["ch0", "ch1", "ch2", "ch3", "ch4", "ch5"])
sub_names = np.array(["a", "b", "c", "d", "e"])

channel_signals = np.array(["vo1a", "vo2a", "vo3a", "vo4a", "v3a", "vt"])
sub_signals = np.array(["magnitude", "frequency", "angle", "rocof", "timestamp"])