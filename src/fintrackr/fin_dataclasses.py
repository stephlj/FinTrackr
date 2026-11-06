"""
These dataclasses hold the structured data from the db in the python layer. 
They're objects that are roughly equivalent to how the information is stored in the db.
They're meant to mesh with the utilities in dbcommons for loading data into the db.

Copyright (c) 2026 Stephanie Johnson
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from dbcommons.dataclass_utils import flat_col_defs

date_format = "%m/%d/%Y"

@dataclass
class Balance:
    balance_date: date = field(metadata={'sql_type':'date', 'csv_parser': lambda s: datetime.strptime(s, date_format)})
    amount: Decimal = field(metadata={'sql_type':'money', 'csv_parser': lambda s: Decimal(s)})
    # account_name: str = field(metadata={'sql_type':'text', 'csv_parser': lambda s: s})

    def __iter__(self):
        yield self.balance_date
        yield self.amount

@dataclass
class Transaction:
    posted_date: date = field(metadata={'sql_type':'date', 'csv_parser': lambda s: datetime.strptime(s, date_format)})
    amount: Decimal = field(metadata={'sql_type':'money', 'csv_parser': lambda s: Decimal(s)})
    description: str = field(metadata={'sql_type':'text', 'csv_parser': lambda s: s})
    # account_name: str

    def __iter__(self):
        yield self.posted_date
        yield self.amount
        yield self.description

# Col defs for interaction with the db layer
BAL_COL_DEFS = flat_col_defs(Balance)
BAL_COL_NAMES = [n for n, _ in BAL_COL_DEFS]
TRANS_COL_DEFS = flat_col_defs(Transaction)
TRANS_COL_NAMES = [n for n, _ in TRANS_COL_DEFS]