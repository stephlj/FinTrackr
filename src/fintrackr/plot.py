"""
Plot various data like account balance over time

Copyright (c) 2026 Stephanie Johnson
"""

import logging
import yaml
import os

from typing import List
from datetime import date

import fintrackr.fin_db

CONFIG_PATH = os.path.join(os.getcwd(),"src","fintrackr","config.yml")

logger = logging.getLogger(__name__)
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

def relative_bal_by_date(rel_to: List[tuple[date, float]], transactions: List[tuple[date, float]]) -> List[tuple[date,float]]:
    """
    Return a tuple of (date, balance) relative to the amount on date in rel_to.
    If rel_to is a List of len>1, uses the chronologically most recent account balance.

    Parameters
    ----------
    rel_to : List[tuple[date, float]]
        Calculate all balances relative to the amount (the float) for the most recent date
    transactions : List[tuple[date, float]]
        List of transactions (date, amount); calculate account balance for each date in
        transactions as a result of each transaction.
    
    Return
    ------
    List[tuple[date, float]]
        Account balances on each date as a result of the list of dated transactions
    """
    # CHeck whether rel_to is None (no balances in range)

    # TODO FIX this sort needs to be on first elements of every tuple
    ref_bal = rel_to.sort()[:-1] # [date, amount] of chronologically most recent account balance


def plot_accnt_balance(accnt_name: str, date_range: List[date], username: str, pw: str) -> None:
    """
    Plot specified account data within date range.
    If no point-in-time account balance is saved in the db, 
    balances will be relative to the first date in the date range.
    If there are multiple balances in date range, balances will be
    relative to the most recent; and the rest will be plotted for reference.

    Uses the db name in config.yml.

    Parameters
    ----------
    accnt_name : str:
        Account for which to plot balances
        TODO set a default primary account in config?
    date_range : List[datetime.date]:
        Date range to plot
    username : str
        username to use to connect to db
    pw : str
        pw to use to connect to db

    Returns
    -------
    None, but a plot is displayed
    """
    
    #This probably goes elsewhere ... 
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)

    amts = FinDB.data_from_date_range(
        data_source = accnt_name, 
        date_range = date_range
    )

    FinDB.close()

    abs_trans = relative_bal_by_date(rel_to = amts["balances"], transactions = amts["transactions"])

    # plot abs_trans - put in its own fn

    # Porbably put all this logic in if name = main and make this plot_balances only
