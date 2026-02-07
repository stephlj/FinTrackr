"""
Plot various data like account balance over time

Copyright (c) 2026 Stephanie Johnson
"""

import logging

from typing import List
from datetime import date

from fintrackr.fin_db import FinDB

logger = logging.getLogger(__name__)
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

def relative_bal_by_date(rel_to: tuple[date, float], transactions: tuple[date, float]) -> tuple[date,float]:
    """
    Return a tuple of (date, balance) relative to the amount on date in rel_to tuple.

    Parameters
    ----------
    rel_to : tuple[date, float]
        Calculate all balances relative to the amount (the float) on this date
    transactions : tuple[date, float]
        List of transactions (date, amount); calculate account balance for each date in
        transactions as a result of each transaction.
    
    Return
    ------
    tuple[date, float]
        Account balances on each date as a result of the list of dated transactions
    """


def data_from_date_range(data_source: str, date_range: List, username: str, pw: str, db_name: str="fin_db") -> List[tuple]:
    """
    Return result of SELECT statement to the db as specified below.
    
    Parameters
    ----------
    data_source : str
        Must exist in data_sources table as a name.
    date_range : List[datetime.date]
        List of length 2: beginning and end dates to return date for.
    username : str
        Username to connect to db
    pw : str
        pw for username to connect to db

    Return
    ------
    dict[tuple]
        key = transactions: All transactions (amount) with data_source_id = data_source and posted_dates
        in range(date_range)
        key = balances: any account balances for this data_source in date_range
    """

    if len(date_range) != 2:
        logger.error(f"Date range must be list of length 2; got instead {date_range}")
        return None

    FinDB = FinDB(user=username, pw=pw, db_name=db_name)

    date_range.sort()

    trans_query = """
        SELECT t.posted_date, t.amount
        FROM transactions AS t
        JOIN data_load_metadata AS m ON m.id = t.metadatum_id
        JOIN data_sources AS s ON s.id = m.data_source_id
        WHERE t.posted_date BETWEEN %s AND %s
        AND s.name=%s;
    """

    transactions = FinDB.execute_query(trans_query, (date_range[0],date_range[1],data_source))

    # All balances in date range
    bal_query = """
        SELECT date, amount
        FROM balances
        WHERE date BETWEEN %s AND %s
        AND balances.accnt_id = (
            SELECT id
            FROM data_sources
            WHERE name=%s
            )
        ;
    """

    balances = FinDB.execute_query(bal_query, (date_range[0],date_range[1],data_source))

    return {"transactions": transactions, "balances": balances}


def plot_accnt_balance(accnt_name: str, date_range: List) -> None:
    """
    Plot specified account data within date range.
    If no point-in-time account balance is saved in the db, 
    balances will be relative to the first date in the date range.

    Parameters
    ----------
    accnt_name : str:
        Account for which to plot balances
        TODO set a default primary account in config?
    date_range : List[datetime.date]:
        Date range to plot

    Returns
    -------
    None, but a plot is displayed
    """
    
    #This probably goes elsewhere ... 
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)


