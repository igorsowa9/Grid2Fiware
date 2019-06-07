import numpy as np

# import own RPI2 scripts
from vm.receive import receive
from vm.settings import *


npdata = np.array(receive(IP_receive, Port_receive, NumData))

print("Values received from RTDS (or fake ones): ", npdata)