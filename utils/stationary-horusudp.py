#!/usr/bin/env python3
import time
import json
import socket
import random

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_host = "127.0.0.1"
udp_port = 55673

lat = 51.16014240902537
lon = 17.150326636817894
alt = 100
random_distance_meters = 10
random_distance_latlon = random_distance_meters * 0.00000898311175

def random_lat() -> float:
    return lat + random_distance_latlon * random.random()

def random_lon() -> float:
    return lon + random_distance_latlon * random.random()

def random_alt() -> float:
    return alt + random_distance_meters * random.random()

while 1:
    # utc time
    utc_time = time.gmtime()

    horus = {
        "type": "PAYLOAD_SUMMARY",
        "latitude": str(random_lat()),
        "longitude": str(random_lon()),
        "altitude": str(random_alt()),
        "callsign": "test",
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", utc_time),
    }

    data = json.dumps(horus)

    print(data)

    udp_socket.sendto(data.encode(), (udp_host, udp_port))

    time.sleep(1)
    pass
