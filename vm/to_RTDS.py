import socket
import sys
import os
import struct
from datetime import datetime, timedelta
import time
import psycopg2
import numpy as np
from pprint import pprint as pp
import platform

# import own RPI2 scripts
from tofloat import tofloat
from send import send
from receive import receive
from settings import settings_fromRTDS, settings_toRTDS, NumData, default_accuracy, dbname
from settings import IP_send, IP_receive, Port_send, Port_receive


# subscribe to the setpoints from the cloud and receive them
# (any storing in DB for grafana necessary?)
# forward them to RTDS

Pset5 = 0.23

data_to_RTDS = [Pset5, -0.2, 0.7, 0.5, 0.1, 0.9, -0.96, -0.6]
a, sa = send(data_to_RTDS, IP_send, Port_send)

print(a)
print(sa)

# if successfull send -> update "time_received"
now = datetime.utcnow()

