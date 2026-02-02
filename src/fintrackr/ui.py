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

def log_balance(accnt_name: str, balance_date: date, balance_amt: float, username: str, pw: str, db_name: str="fin_db") -> None:
    """
    Log an account balance in the database

    TODO allow csv rather than/in addition to str?

    Parameters
    ----------
    accnt_name : str
        Must exist in data_sources table as a name.
    balance_date : datetime.date
        Date that this was the account's balance.
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

    FinDB = FinDB(user=username, pw=pw, db_name=db_name)

    result = FinDB.add_balance(accnt = accnt_name, bal_date = balance_date, bal_amt = balance_amt)

    if result == 1:
        logger.info("Successfully logged balance of {balance_amt} to account {account_name} on date {balance_date} in {db_name}")
    else:
        logger.warning("Unsuccessful attempt to log balance of {balance_amt} to account {account_name} on date {balance_date} in {db_name}")

# Correct balance (in case a balance was entered wrong)

# Load transactions (check file en route)

