import socket
import sys
import struct
import numpy as np
import time

# data is an array

def send(data, IP, Port):
	
	# Create a UDP socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	server_address = (IP, Port)
	NumElements = len(data)

	# create the array
	a = struct.pack('>f', data[0])
	for i in range(1,NumElements):
			a += struct.pack('>f', data[i])

	sent = sock.sendto(a, server_address)
	print("RPI2, send: data sent ot RTDS(",IP,Port,"): ", data)
	
	return a, server_address
