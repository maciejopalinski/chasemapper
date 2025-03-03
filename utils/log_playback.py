#!/usr/bin/env python
#
#   ChaseMapper - Log File Playback
#
#   Copyright (C) 2019  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
#
#   TODO:
#       [x] Playback of basic log entries (car position, balloon telemetry, bearings)
#       [ ] Playback and display of balloon prediction data
#       [ ] Skip forward / back through file
#   
import json
import socket
import sys
import time
import datetime
import traceback
from dateutil.parser import *


def send_bearing(json_data, udp_port=55672, hostname='<broadcast>'):
    """
    Grab bearing data out of a json log entry and send it via UDP.

    Example bearing line:
    {"bearing": 112.0, 
    "confidence": 47.24745556875042, 
    "power": 25.694795608520508, 
    "raw_bearing_angles": [0.0, 1.0, ... 359.0, 360.0], 
    "raw_doa": [-4.722, -4.719, ... -4.724, -4.722], 
    "source": "kerberos-sdr", 
    "bearing_type": "relative", 
    "log_time": "2019-08-19T11:21:51.714657+00:00", 
    "type": "BEARING", 
    "log_type": "BEARING"}
    """
    # Also get bearings of form: 
    # {"type": "BEARING", "bearing_type": "absolute", "source": "EasyBearing", "latitude": -34.9016115, 
    #"longitude": 138.58986819999998, "bearing": 0, "log_type": "BEARING", "log_time": "2021-12-10T07:33:14.156227+00:00"}

    packet = json_data

    packet['replay_time'] = json_data['log_time']

    if 'kerberos' in json_data['source']:
        # Log data from the kerberos has been flipped in bearing already. Need to make sure this isn't done twice.
        packet['source'] = 'replay'


    # Set up our UDP socket
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    # Set up socket for broadcast, and allow re-use of the address
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('',udp_port))
    try:
        s.sendto(json.dumps(packet).encode('ascii'), (hostname, udp_port))
    except socket.error as e:
        s.sendto(json.dumps(packet).encode('ascii'), ('127.0.0.1', udp_port))

    if hostname != '<broadcast>':
        s.sendto(json.dumps(packet).encode('ascii'), ('127.0.0.1', udp_port))


def send_car_position(json_data, udp_port=55672):
    """ 
    Grab car position data from a json log entry and emit it

    {"comment": "CAR", 
    "log_time": "2019-08-19T11:21:52.303204+00:00", 
    "lon": 138.68833, 
    "log_type": "CAR POSITION", 
    "time": "2019-08-19T11:21:52.300687+00:00", 
    "lat": -34.71413666666667, 
    "alt": 69.3, 
    "speed": 17.118923473141397, 
    "heading": 27.53170956683383}
    """

    packet = {
        'type' : 'GPS',
        'latitude' : json_data['lat'],
        'longitude' : json_data['lon'],
        'altitude': json_data['alt'],
        'speed': json_data['speed'],
        'valid': True,
        'replay_time': json_data['log_time']
    }

    if 'heading' in json_data:
        packet['heading'] = json_data['heading']

    # Set up our UDP socket
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    # Set up socket for broadcast, and allow re-use of the address
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('',udp_port))
    try:
        s.sendto(json.dumps(packet).encode('ascii'), ('<broadcast>', udp_port))
    except socket.error:
        s.sendto(json.dumps(packet).encode('ascii'), ('127.0.0.1', udp_port))


def send_balloon_telemetry(json_data, udp_port=55672):
    """ Grab balloon telemetry data from a JSON log entry and emit it

    {"sats": -1, 
    "log_time": "2019-08-21T11:02:25.596045+00:00", 
    "temp": -1, 
    "lon": 138.000000, 
    "callsign": "HORUS", 
    "time": "2019-08-21T11:02:16+00:00", 
    "lat": -34.000000, 
    "alt": 100, 
    "log_type": "BALLOON TELEMETRY"}

    """

    packet = {
        'type' : 'PAYLOAD_SUMMARY',
        'latitude' : json_data['lat'],
        'longitude' : json_data['lon'],
        'altitude': json_data['alt'],
        'callsign': json_data['callsign'],
        'time': parse(json_data['time']).strftime("%H:%M:%S"),
        'comment': "Log Playback",
        'replay_time': json_data['log_time']
    }

    # Set up our UDP socket
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    # Set up socket for broadcast, and allow re-use of the address
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('',udp_port))
    try:
        s.sendto(json.dumps(packet).encode('ascii'), ('<broadcast>', udp_port))
    except socket.error:
        s.sendto(json.dumps(packet).encode('ascii'), ('127.0.0.1', udp_port))


def playback_json(filename, udp_port=55672, speed=1.0, start_time = 0, hostname='<broadcast>'):
    """ Read in a JSON log file and play it back in real-time, or with a speed factor """

    with open(filename, 'r') as _log_file:

        try:
            _first_line = _log_file.readline()
            _log_data = json.loads(_first_line)
            _previous_time = parse(_log_data['log_time'])
            _first_time = _previous_time
        except Exception as e:
            print("First line of file must be a valid log entry - %s" % str(e))
            return

        for _line in _log_file:
            try:
                _log_data = json.loads(_line)

                _new_time = parse(_log_data['log_time'])

                _time_delta = (_new_time - _previous_time).total_seconds()
                _previous_time = _new_time

                # Running timer
                _run_time = (_new_time - _first_time).total_seconds()


                if _run_time < start_time:
                    continue

                _time_min = int(_run_time)//60
                _time_sec = _run_time%60.0

                if (_time_delta < 100):
                    time.sleep(_time_delta/speed)

                if _log_data['log_type'] == 'CAR POSITION':
                    send_car_position(_log_data, udp_port)
                    print("%s - %02d:%.2f - Car Position" % (_log_data['log_time'], _time_min, _time_sec))
                
                elif _log_data['log_type'] == 'BEARING':
                    send_bearing(_log_data, udp_port, hostname=hostname)
                    print("%s - %02d:%.2f - Bearing Data" % (_log_data['log_time'], _time_min, _time_sec))
                
                elif _log_data['log_type'] == 'BALLOON TELEMETRY':
                    send_balloon_telemetry(_log_data, udp_port)
                    print("%02d:%.2f - Balloon Telemetry (%s)" % (_time_min, _time_sec, _log_data['callsign']))
                
                elif _log_data['log_type'] == 'PREDICTION':
                    print("%02d:%.2f - Prediction (Not re-played)" % (_time_min, _time_sec))

                else:
                    print("%02d:%.2f - Unknown: %s" % (_time_min, _time_sec, _log_data['log_type']))

            except Exception as e:
                print("Invalid log entry: %s" % str(e))





if __name__ == '__main__':

    filename = ""
    speed = 1.0
    start_time = 0
    hostname = 'localhost'
    udp_port = 55672

    if len(sys.argv) == 2:
        filename = sys.argv[1]
    elif len(sys.argv) == 3:
        filename = sys.argv[1]
        speed = float(sys.argv[2])
    elif len(sys.argv) == 4:
        filename = sys.argv[1]
        speed = float(sys.argv[2])
        start_time = float(sys.argv[3])*60
    else:
        print("USAGE: python log_playback.py filename.log <speed_multiplier> <start_time>")

    playback_json(filename, udp_port, speed, start_time, hostname=hostname)

