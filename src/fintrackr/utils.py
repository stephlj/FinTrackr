from dataclasses import dataclass
from datetime import date


@dataclass
class Transaction:
    date: date
    amount: float

    def __iter__(self):
        yield self.date
        yield self.amount