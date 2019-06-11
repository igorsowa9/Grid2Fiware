import platform, sys

dbname = 'SAU_PC'

#if str(platform.machine())=='x86_64':
#    IPinput = input("input your IP (leave empty for previous one): ")
#    if IPinput == "":
#        IPinput = '137.226.124.77'
#else: IPinput = '134.130.169.61' # for raspberry

# IP_send = '134.130.169.61' # of GTNET?
IP_receive = '134.130.169.12' # should be updated by the current public (depending on configuration) IP address?
Port_send = 12334
Port_receive = 12334

NumData = 18
# name, mtype, phaseid, nodeid, // others: time1, measurementvalue, accuracyvalue
default_accuracy = 1
settings_fromRTDS = [['P5max', 28, 'ABCN', 4], ['P5min', 29, 'ABCN', 4], ['Q5max', 30, 'ABCN', 4], ['Q5min', 31, 'ABCN', 4],
            ['P7max', 28, 'ABCN', 6], ['P7min', 29, 'ABCN', 6], ['Q7max', 30, 'ABCN', 6], ['Q7min', 31, 'ABCN', 6],
            ['P9max', 28, 'ABCN', 8], ['P9min', 29, 'ABCN', 8], ['Q9max', 30, 'ABCN', 8], ['Q9min', 31, 'ABCN', 8],
            ['Pload2', 10, 'ABCN', 1], ['Qload2', 12, 'ABCN', 1],
            ['Pload3', 10, 'ABCN', 2], ['Qload3', 12, 'ABCN', 2],
            ['Pload4', 10, 'ABCN', 3], ['Qload4', 12, 'ABCN', 3],
            ['Pload5', 10, 'ABCN', 4], ['Qload5', 12, 'ABCN', 4],
            ['Pload6', 10, 'ABCN', 5], ['Qload6', 12, 'ABCN', 5],
            ['Pload7', 10, 'ABCN', 6], ['Qload7', 12, 'ABCN', 6],
            ['Pload8', 10, 'ABCN', 7], ['Qload8', 12, 'ABCN', 7],
            ['Pload10', 10, 'ABCN', 9], ['Qload10', 12, 'ABCN', 9]]

# name, node_id, id (from networktopology.injections), control type - without slack generator, only converters and flexible loads
settings_toRTDS = [['P5gen_pc', 4, 1, 20, 2], ['Q5gen_pc', 4, 1, 20, 4],
                   ['P7gen_pc', 6, 2, 21, 2], ['Q7gen_pc', 6, 2, 21, 4],
                   ['Q9gen_pc', 8, 3, 22, 2], ['Q9gen_pc', 8, 3, 22, 4],
                   ['P8fload_pc', 7, 4, 23, 2], ['Q8fload_pc', 7, 4, 23, 4]]
