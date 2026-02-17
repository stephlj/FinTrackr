"""
User interface to the database. (Command line for now.)

Copyright (c) 2026 Stephanie Johnson
"""

import logging

from datetime import date

from fintrackr.fin_db import FinDB

logger = logging.getLogger(__name__)

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

# TODO add click interface

def log_balance(accnt_name: str, balance_date: tuple[int], balance_amt: float, username: str, pw: str, db_name: str="fin_db") -> None:
    """
    Log an account balance in the database

    TODO allow csv rather than/in addition to str?

    Parameters
    ----------
    accnt_name : str
        Equivalent to name column in data_sources (will be added if doesn't exist in that table)
    balance_date : tuple[int]
        Date that this was the account's balance, of form ({year}, {month}, {day}),
        e.g. (2025,8,5).
    balance_amt : float
        Account balance on balance_date
    username : str
        User to use to connect to db
    pw : str
        User's pw to connect to db
    db_name : str
        db to connect to (default fin_db; this is not hard-coded for testing purposes)

    Returns
    -------
    None
    """

    d = date(year=balance_date[0], month=balance_date[1],day=balance_date[2])

    FinDB = FinDB(user=username, pw=pw, db_name=db_name)

    result = FinDB.add_balance(accnt = accnt_name, bal_date = d, bal_amt = balance_amt)

    if result == 1:
        logger.info("Successfully logged balance of {balance_amt} to account {account_name} on date {balance_date} in {db_name}")
    else:
        logger.warning("Unsuccessful attempt to log balance of {balance_amt} to account {account_name} on date {balance_date} in {db_name}")

# TODO add Correct balance (in case a balance was entered wrong)

# TODO add Load transactions (check file en route)

