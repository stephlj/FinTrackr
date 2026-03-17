"""
Small utilities used by multiple modules.

Copyright (c) 2026 Stephanie Johnson
"""

import os

from dataclasses import dataclass
from datetime import date

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

CONFIG_PATH = os.path.join(os.getcwd(),"src","fintrackr","config.yml")

@dataclass
class Transaction:
    date: date
    amount: float

    def __iter__(self):
        yield self.date
        yield self.amount