"""PyEnergir Output Module.

This module defines the different output functions:
* text
* influxdb
* json
"""
import json
import datetime
import pprint

from pyenergir import ENERGIR_TIMEZONE


def output_text(account, all_data):
    """Format data to get a readable output."""
    pprint.pprint(account)
    pprint.pprint(all_data)


def output_json(data):
    """Print data as Json."""
    print(json.dumps(data))
