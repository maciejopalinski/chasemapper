#!/usr/bin/env python2.7
#
#   Project Horus - Browser-Based Chase Mapper
#   Log File Parsing
#
#   Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import argparse
import datetime
import json
import logging
import sys
import numpy as np
import matplotlib.pyplot as plt
from chasemapper.earthmaths import *
from chasemapper.geometry import *
from dateutil.parser import parse
from cusfpredict.reader import *


def read_file(filename):
    """ Read log file, and output an array of dicts. """
    _output = []

    _f = open(filename, 'r')
    for _line in _f:
        try:
            _data = json.loads(_line)
            _output.append(_data)
        except Exception as e:
            logging.debug("Error reading line: %s" % str(e))

    logging.info("Read %d log entries." % len(_output))

    return _output


def stringify_entry(entry):
    """ Convert a balloon telemetry entry to a string """
    _out = "%s,%.6f,%.6f,%d\n" % (entry['time'], entry['lat'], entry['lon'], entry['alt'])
    return _out

def extract_data(log_entries, csv_dump=None):
    """ Step through the log entries, and extract:
    - Car position telemetry
    - Balloon positions
    - Predictions 
    """

    # There's only ever going to be one car showing up on the map, so we just output a list.
    _car = []
    # We might have more than one balloon though, so we use a dictionary, with one entry per callsign.
    _telemetry = {}

    if csv_dump is not None:
        csv_out = open(csv_dump, 'w')

    for _entry in log_entries:

        if _entry['log_type'] == "CAR POSITION":
            _car.append(_entry)

        elif _entry['log_type'] == "BALLOON TELEMETRY":
            # Extract the callsign.
            _call = _entry['callsign']

            if _call not in _telemetry:
                _telemetry[_call] = {'telemetry': [], 'predictions': []}

            _telemetry[_call]['telemetry'].append(_entry)

            if csv_dump is not None:
                csv_out.write(stringify_entry(_entry))

        elif _entry['log_type'] == "PREDICTION":
            # Extract the callsign.
            _call = _entry['callsign']

            if _call not in _telemetry:
                _telemetry[_call] = {'telemetry': [], 'predictions': []}

            _telemetry[_call]['predictions'].append(_entry)

    logging.info("Extracted %d Car Positions" % len(_car))
    for _call in _telemetry:
        logging.info("Callsign %s: Extracted %d telemetry positions, %d predictions." % (_call, len(_telemetry[_call]['telemetry']), len(_telemetry[_call]['predictions'])))


    if csv_dump is not None:
        csv_out.close()

    return (_car, _telemetry)



def flight_stats(telemetry, ascent_threshold = 3.0, descent_threshold=-5.0,  landing_threshold = 3.0):
    """ Process a set of balloon telemetry, and calculate some statistics about the flight """

    asc_rate_avg_length = 5

    _stats = {
        'ascent_rates': np.array([]),
        'positions': [],
        'raw_ascent_rates': [],
        'altitudes': [],
        'speeds': [],
        'headings': []
    }

    _flight_segment = "UNKNOWN"

    _track = GenericTrack() 

    for _entry in telemetry:
        # Fix timestamps if they do not have a timezone
        if _entry['time'].endswith('Z') or _entry['time'].endswith('+00:00'):
            pass
        else:
            _entry['time'] += "Z"

        if _entry['log_time'].endswith('Z') or _entry['log_time'].endswith('+00:00'):
            pass
        else:
            _entry['log_time'] += "Z"



        # Produce a dict which we can pass into the GenericTrack object.
        _position = {
            'time': parse(_entry['time']),
            'lat': _entry['lat'],
            'lon': _entry['lon'],
            'alt': _entry['alt']
        }


        _stats['positions'].append([_position['time'], _position['lat'], _position['lon'], _position['alt']])
        _state = _track.add_telemetry(_position)

        #print(_state)

        if _state == None:
            continue

        _stats['altitudes'].append(_state['alt'])
        _stats['raw_ascent_rates'].append(_state['ascent_rate'])
        _stats['speeds'].append(_state['speed'])
        _stats['headings'].append(_state['heading'])

        if len(_stats['ascent_rates']) < asc_rate_avg_length:
            # Not enough data to make any judgements about the state of the flight yet.
            _stats['ascent_rates'] = np.append(_stats['ascent_rates'], _state['ascent_rate'])
        else:
            # Roll the array, and add the new value on the end.
            _stats['ascent_rates'] = np.roll(_stats['ascent_rates'], -1)
            _stats['ascent_rates'][-1] = _state['ascent_rate']

            _mean_asc_rate = np.mean(_stats['ascent_rates'])

            if _flight_segment == "UNKNOWN":
                # Make a determination on flight state based on what we know now.
                if _mean_asc_rate > ascent_threshold:
                    _flight_segment = "ASCENT"
                    _stats['launch'] = [_state['time'], _state['lat'], _state['lon'], _state['alt']]
                    logging.info("Detected Launch: %s, %.5f, %.5f, %dm" % 
                        (_state['time'].isoformat(), _state['lat'], _state['lon'], _state['alt']))
                elif _mean_asc_rate < descent_threshold:
                    _flight_segment = "DESCENT"
                else:
                    pass

            if _flight_segment == "ASCENT":
                if _track.track_history[-1][3] < _track.track_history[-2][3]:
                    # Possible detection of burst.
                    if 'burst_position' not in _stats:
                        _stats['burst_position'] = _track.track_history[-2]
                        logging.info("Detected Burst: %s, %.5f, %.5f, %dm" % (
                            _stats['burst_position'][0].isoformat(),
                            _stats['burst_position'][1],
                            _stats['burst_position'][2],
                            _stats['burst_position'][3]
                            ))
                        logging.info("Average ascent rate: %.2f" % np.mean(_stats['raw_ascent_rates']))

                if _mean_asc_rate < descent_threshold:
                    _flight_segment = "DESCENT"
                    continue

            if _flight_segment == "DESCENT":
                print(abs(_mean_asc_rate))
                if abs(_mean_asc_rate) < landing_threshold:
                    _stats['landing'] = [parse(_entry['log_time']), _state['lat'], _state['lon'], _state['alt']]
                    logging.info("Detected Landing: %s, %.5f, %.5f, %dm" % 
                        (_entry['log_time'], _state['lat'], _state['lon'], _state['alt']))


                    _flight_segment = "LANDED"
                    return _stats
            
            #print(_flight_segment)

    return _stats


def calculate_predictor_error(predictions, landing_time, lat, lon, alt):
    """ Process a list of predictions, and determine the landing position error for each one """


    _output = []

    _landing = (lat, lon, alt)


    for _predict in predictions:
        _predict_time = _predict['log_time']

        # Append on a timezone indicator if the time doesn't have one.
        if _predict_time.endswith('Z') or _predict_time.endswith('+00:00'):
            pass
        else:
            _predict_time += "Z"

        if landing_time != None:
            if parse(_predict_time) > (landing_time-datetime.timedelta(0,30)):
                break

        _predict_altitude = _predict['pred_path'][0][2]
        _predict_landing = (_predict['pred_landing'][0], _predict['pred_landing'][1], _predict['pred_landing'][2])


        _pos_info = position_info(_landing, _predict_landing)

        logging.debug("Prediction %s: Altitude %d, Predicted Landing: %.4f, %.4f Prediction Error: %.1f km, %s" % (
            _predict_time,
            int(_predict_altitude),
            _predict['pred_landing'][0],
            _predict['pred_landing'][1],
            (_pos_info['great_circle_distance']/1000.0),
            bearing_to_cardinal(_pos_info['bearing'])
            ))

        _output.append([
            parse(_predict_time),
            _pos_info['great_circle_distance']/1000.0,
            _pos_info['bearing'],
            _predict_altitude
            ])

    return _output


def calculate_abort_error(predictions, landing_time, lat, lon, alt):
    """ Process a list of predictions, and determine the landing position error for each one """


    _output = []

    _landing = (lat, lon, alt)


    for _predict in predictions:

        # Check there is an abort prediction available.
        if len(_predict['abort_landing']) == 0:
            continue

        _predict_time = _predict['log_time']


        # Append on a timezone indicator if the time doesn't have one.
        if _predict_time.endswith('Z') or _predict_time.endswith('+00:00'):
            pass
        else:
            _predict_time += "Z"

        if landing_time != None:
            if parse(_predict_time) > (landing_time-datetime.timedelta(0,30)):
                break

        _predict_altitude = _predict['abort_path'][0][2]
        _predict_landing = (_predict['abort_landing'][0], _predict['abort_landing'][1], _predict['abort_landing'][2])


        _pos_info = position_info(_landing, _predict_landing)

        logging.debug("Abort Prediction %s: Altitude %d, Predicted Landing: %.4f, %.4f Prediction Error: %.1f km, %s" % (
            _predict_time,
            int(_predict_altitude),
            _predict['abort_landing'][0],
            _predict['abort_landing'][1],
            (_pos_info['great_circle_distance']/1000.0),
            bearing_to_cardinal(_pos_info['bearing'])
            ))

        _output.append([
            parse(_predict_time),
            _pos_info['great_circle_distance']/1000.0,
            _pos_info['bearing'],
            _predict_altitude
            ])

    return _output


def plot_predictor_error(flight_stats, predictor_errors, abort_predictor_errors=None, callsign = ""):

    # Get launch time.
    _launch_time = flight_stats['launch'][0]

    # Generate datasets of time-since-launch and altitude.
    _flight_time = []
    _flight_alt = []
    for _entry in flight_stats['positions']:
        _ft = (_entry[0]-_launch_time).total_seconds()/60.0
        if _ft > 0:
            _flight_time.append(_ft)
            _flight_alt.append(_entry[3])

    # Generate datasets of time-since-launch and altitude.
    _predict_time = []
    _predict_alt = []
    _predict_error = []
    for _entry in predictor_errors:
        _ft = (_entry[0]-_launch_time).total_seconds()/60.0
        if _ft > 0:
            _predict_time.append(_ft)
            _predict_error.append(_entry[1])
            _predict_alt.append(_entry[3])


    # Altitude vs Time
    plt.figure()
    plt.plot(_flight_time, _flight_alt)
    plt.grid()
    plt.xlabel("Time (minutes)")
    plt.ylabel("Altitude (metres)")
    plt.title("Flight Profile - %s" % callsign)

    # Prediction error vs time.
    plt.figure()
    plt.plot(_predict_time, _predict_error, label='Full Flight')

    if abort_predictor_errors != None:
        _abort_predict_time = []
        _abort_predict_error = []
        for _entry in abort_predictor_errors:
            _ft = (_entry[0]-_launch_time).total_seconds()/60.0
            if _ft > 0:
                _abort_predict_time.append(_ft)
                _abort_predict_error.append(_entry[1])

        plt.plot(_abort_predict_time, _abort_predict_error, label='Abort Prediction')
        plt.legend()
    
    plt.xlabel("Time (minutes)")
    plt.ylabel("Landing Prediction Error (km)")
    plt.title("Landing Prediction Error - %s" % callsign)
    plt.grid()

    plt.figure()
    _peak_idx = np.argmax(_predict_alt)

    plt.plot(_predict_error[_peak_idx:], _predict_alt[_peak_idx:])
    plt.xlabel("Prediction error (km)")
    plt.ylabel("Flight altitude (m)")
    plt.title("Landing Prediction Error - %s" % callsign)
    plt.grid()


def plot_wind_trace(stats, title="", gfs_file=None, landing=None, ascent=True):
    """ Plot the wind trace for the descent part of the flight """

    _altitude = stats['altitudes']
    _speed = stats['speeds']
    _heading = stats['headings']

    # Find peak altitude
    _peak_idx = np.argmax(_altitude)

    if ascent:
        # Only use descent data
        _altitude = np.array(_altitude[:_peak_idx])
        _speed = np.array(_speed[:_peak_idx])
        _heading = np.array(_heading[:_peak_idx])
    else:
        # Only use descent data
        _altitude = np.array(_altitude[_peak_idx:])
        _speed = np.array(_speed[_peak_idx:])
        _heading = np.array(_heading[_peak_idx:])

    if gfs_file is not None:
        # Read in supplied GFS file.
        _gfs = read_cusf_gfs(gfs_file)
        
        logging.info("Read in GFS data for time %s." % _gfs['timestamp'].isoformat())        

        _lat_idx = np.argmin(np.abs(_gfs['latitudes']-landing[0]))
        _lon_idx = np.argmin(np.abs(_gfs['longitudes']-landing[1]))

        _gfs_alts = _gfs['data'][:,_lat_idx, _lon_idx][:,0]
        _gfs_speed = _gfs['data'][:,_lat_idx, _lon_idx][:,3]
        _gfs_heading = _gfs['data'][:,_lat_idx, _lon_idx][:,4]

    # Speed plot
    plt.figure()
    plt.plot(_speed, _altitude, label=title)

    if gfs_file is not None:
        plt.plot(_gfs_speed, _gfs_alts, label='GFS')

    plt.ylabel("Altitude (m)")
    plt.xlabel("Absolute Speed (m/s)")
    plt.title("Wind Speed - " + title)
    plt.grid()
    plt.legend()

    plt.figure()
    # Plot actual data
    plt.plot((_heading+180.0)%360.0, _altitude, label=title)

    if gfs_file is not None:
        plt.plot(_gfs_heading, _gfs_alts, label='GFS')

    plt.ylabel("Altitude (m)")
    plt.xlabel("Wind Heading (Degrees True)")
    plt.title("Wind Heading - " + title)
    plt.grid()
    plt.legend()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str, help="Input log file.")
    parser.add_argument("-c", "--config", type=str, default="horusmapper.cfg", help="Configuration file.")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output.")
    parser.add_argument("--predict-error", action="store_true", default=False, help="Calculate Prediction Error.")
    parser.add_argument("--abort-predict-error", action="store_true", default=False, help="Calculate Abort Prediction Error.")
    parser.add_argument("--landing-lat", type=float, default=None, help="Override Landing Latitude")
    parser.add_argument("--landing-lon", type=float, default=None, help="Override Landing Longitude")
    parser.add_argument("--wind-trace", action="store_true", default=False, help="Plot wind trace.")
    parser.add_argument("--gfs-file", type=str, default=None, help="Overlay GFS data on wind trace.")
    parser.add_argument("--csv-dump", type=str, default=None, help="Dump telemetry to CSV file.")
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        _log_level = logging.DEBUG
    else:
        _log_level = logging.INFO

    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', stream=sys.stdout, level=_log_level)


    _log_entries = read_file(args.filename)

    _car, _telemetry = extract_data(_log_entries, csv_dump=args.csv_dump)

    for _call in _telemetry:
        logging.info("Processing Callsign: %s" % _call)
        _stats = flight_stats(_telemetry[_call]['telemetry'])

        if ('landing' in _stats) and ('launch' in _stats):
            _total_flight = position_info((_stats['launch'][1],_stats['launch'][2],_stats['launch'][3]),(_stats['landing'][1], _stats['landing'][2], _stats['landing'][3]))
            logging.info("%s Flight Distance: %.2f km" % (_call, _total_flight['great_circle_distance']/1000.0))

        if args.predict_error:
            if (args.landing_lat) != None and (args.landing_lon != None):
                _predict_errors = calculate_predictor_error(_telemetry[_call]['predictions'], None, args.landing_lat, args.landing_lon, 0)
                if args.abort_predict_error:
                    _abort_predict_errors = calculate_abort_error(_telemetry[_call]['predictions'], None, args.landing_lat, args.landing_lon, 0)
                else:
                    _abort_predict_errors = None
                plot_predictor_error(_stats, _predict_errors, _abort_predict_errors, _call)

                plot_wind_trace(_stats, title=_call)

            elif 'landing' in _stats:
                _time = _stats['landing'][0]
                _lat = _stats['landing'][1]
                _lon = _stats['landing'][2]
                _alt = _stats['landing'][3]
                _predict_errors = calculate_predictor_error(_telemetry[_call]['predictions'], _time, _lat, _lon, _alt)
                if args.abort_predict_error:
                    _abort_predict_errors = calculate_abort_error(_telemetry[_call]['predictions'], _time, _lat, _lon, _alt)
                else:
                    _abort_predict_errors = None

                plot_predictor_error(_stats, _predict_errors, _abort_predict_errors, _call)

                plot_wind_trace(_stats, title=_call, gfs_file=args.gfs_file, landing=[_lat, _lon])

            else:
                logging.error("No landing position available.")

    if args.predict_error or args.wind_trace:
        plt.show()



