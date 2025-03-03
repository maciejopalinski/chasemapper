#!/usr/bin/env python
#
#   Project Horus - Log read operations
#
#   Copyright (C) 2019  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import datetime
import json
import logging
import os
import pytz
import time

# from datetime import datetime
from dateutil.parser import parse


def read_file(filename):
    """ Read log file, and output an array of dicts. """
    _output = []

    _f = open(filename, "r")
    for _line in _f:
        try:
            _data = json.loads(_line)
            _output.append(_data)
        except Exception as e:
            logging.debug("Error reading line: %s" % str(e))
    if len(_output) != 0:
        logging.info("Read %d log entries from %s" % (len(_output), filename))

    return _output


def read_last_balloon_telemetry():
    """ Read last balloon telemetry. Need to work back from last file to find balloon telemetry and read the last entry - don't return until whole file scanned
        """
    _lasttelemetry = []
    dirs = sorted(
        os.listdir("./logs"), reverse=True
    )  # Generate a reverse sorted list - will have to look through to find last log_file with telemetry
    for file in dirs:
        if file.endswith(".log"):
            telemetry_found = False
            try:
                log = read_file("./logs/" + file)
            except Exception as e:
                logging.debug("Error reading file - maybe in use: %s" % str(e))

            for _entry in log:
                if _entry["log_type"] == "BALLOON TELEMETRY":
                    telemetry_found = True
                    _last_telemetry = _entry

            if telemetry_found == True:
                _last_telemetry["time_dt"] = parse(_last_telemetry.pop("time"))
                return _last_telemetry
