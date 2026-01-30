"""
Plot various data like account balance over time

Copyright (c) 2026 Stephanie Johnson
"""

import logging

from typing import List

logger = logging.getLogger(__name__)
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)


def plot_accnt_balance(accnt_name: str, date_range: List) -> None:
    """
    Docstring for plot_accnt_balance
    
    :param accnt_name: Description
    :type accnt_name: str
    :param date_range: Description
    :type date_range: List
    """
    
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
