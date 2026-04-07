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

SQL_to_python_types = {"date" : "date",
                       "money" : "float64",
                       "text" : "str"}

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

def equiv_col_types(col1: str, col2: str) -> bool:
    """
    Assess whether col1 and col2 match any key, value pair in SQL_to_python_types.

    TODO should this be a dataclass rather than a dict and a function?

    Parameters
    ----------
    col1, col2 : str
        Strings to compare
    
    Return
    ------
    bool, True if a match is found
    """

    if col1 in SQL_to_python_types and SQL_to_python_types[col1] == col2:
        return True
    elif col2 in SQL_to_python_types and SQL_to_python_types[col2] == col1:
        return True
    else:
        return False