"""
These dataclasses hold the structured data from the db in the python layer. 
They're objects that are roughly equivalent to how the information is stored in the db.

Copyright (c) 2026 Stephanie Johnson
"""

from dataclasses import dataclass
from datetime import date

@dataclass
class Balance:
    date: date
    amount: float
    # account_name: str

    def __iter__(self):
        yield self.date
        yield self.amount

@dataclass
class Transaction:
    date: date
    amount: float
    # description: str # TODO carry description text around e.g. for plotting
    # account_name: str

    def __iter__(self):
        yield self.date
        yield self.amount

@dataclass
class Col_Def:
    # db column definitions (name and type, e.g. "amount", "money")
    col_name: str
    col_type: str

    def __iter__(self):
        yield self.col_name
        yield self.col_type