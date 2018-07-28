#!/usr/bin/env python
#
#   Project Horus - Browser-Based Chase Mapper - Config Reader
#
#   Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import logging

try:
    # Python 2
    from ConfigParser import RawConfigParser
except ImportError:
    # Python 3
    from configparser import RawConfigParser


default_config = {
    # Start location for the map (until either a chase car position, or balloon position is available.)
    'default_lat': -34.9,
    'default_lon': 138.6,

    'payload_max_age': 180,

    # Predictor settings
    'pred_enabled': False,  # Enable running and display of predicted flight paths.
    # Default prediction settings (actual values will be used once the flight is underway)
    'pred_model': "Disabled",
    'pred_desc_rate': 6.0,
    'pred_burst': 28000,
    'show_abort': True, # Show a prediction of an 'abort' paths (i.e. if the balloon bursts *now*)
    'pred_update_rate': 15 # Update predictor every 15 seconds.
    }


def parse_config_file(filename):
	""" Parse a Configuration File """

	chase_config = default_config.copy()

	config = RawConfigParser()
	config.read(filename)

	# Map Defaults
	chase_config['flask_host'] = config.get('map', 'flask_host')
	chase_config['flask_port'] = config.getint('map', 'flask_port')
	chase_config['default_lat'] = config.get('map', 'default_lat')
	chase_config['default_lon'] = config.get('map', 'default_lon')
	chase_config['payload_max_age'] = config.getint('map', 'payload_max_age')


	# GPSD Settings
	chase_config['car_gpsd_host'] = config.get('gpsd','gpsd_host')
	chase_config['car_gpsd_port'] = config.getint('gpsd','gpsd_port')

	# Predictor
	chase_config['pred_enabled'] = config.getboolean('predictor', 'predictor_enabled')
	chase_config['pred_burst'] = config.getfloat('predictor', 'default_burst')
	chase_config['pred_desc_rate'] = config.getfloat('predictor', 'default_descent_rate')
	chase_config['pred_binary'] = config.get('predictor','pred_binary')
	chase_config['pred_gfs_directory'] = config.get('predictor', 'gfs_directory')
	chase_config['pred_model_download'] = config.get('predictor', 'model_download')

	# Telemetry Source Profiles

	_profile_count = config.getint('profile_selection', 'profile_count')
	_default_profile = config.getint('profile_selection', 'default_profile')

	chase_config['selected_profile'] = ""
	chase_config['profiles'] = {}

	for i in range(1,_profile_count+1):
		_profile_section = "profile_%d" % i
		try:
			_profile_name = config.get(_profile_section, 'profile_name')
			_profile_telem_source_type = config.get(_profile_section, 'telemetry_source_type')
			_profile_telem_source_port = config.getint(_profile_section, 'telemetry_source_port')
			_profile_car_source_type = config.get(_profile_section, 'car_source_type')
			_profile_car_source_port = config.getint(_profile_section, 'car_source_port')

			chase_config['profiles'][_profile_name] = {
				'name': _profile_name,
				'telemetry_source_type': _profile_telem_source_type,
				'telemetry_source_port': _profile_telem_source_port,
				'car_source_type': _profile_car_source_type,
				'car_source_port': _profile_car_source_port
			}
			if _default_profile == i:
				chase_config['selected_profile'] = _profile_name

		except Exception as e:
			logging.error("Error reading profile section %d - %s" % (i, str(e)))

	if len(chase_config['profiles'].keys()) == 0:
		logging.critical("Could not read any profile data!")
		return None

	if chase_config['selected_profile'] not in chase_config['profiles']:
		logging.critical("Default profile selection does not exist.")
		return None

	return chase_config




def read_config(filename, default_cfg="horusmapper.cfg.example"):
	""" Read in a Horus Mapper configuration file,and return as a dict. """

	try:
		config_dict = parse_config_file(filename)
	except Exception as e:
		logging.error("Could not parse %s, trying default: %s" % (filename, str(e)))
		try:
			config_dict = parse_config_file(default_cfg)
		except Exception as e:
			logging.critical("Could not parse example config file! - %s" % str(e))
			config_dict = None

	return config_dict

if __name__ == "__main__":
	import sys
	print(read_config(sys.argv[1]))

