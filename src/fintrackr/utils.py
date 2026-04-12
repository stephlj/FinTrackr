"""
Small utilities used by multiple modules.

Copyright (c) 2026 Stephanie Johnson
"""

import os

from datetime import date, datetime

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

CONFIG_PATH = os.path.join(os.getcwd(),"src","fintrackr","config.yml")

date_format = "%m/%d/%Y"

def valid_date(date_string: str) -> bool:
    """
    Determine if a string contains a date in acceptable format.

    Parameters
    ----------
    date_string : str
        string to test
    
    Return
    ------
    bool, True if string can be converted to date_format above
    """

    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False