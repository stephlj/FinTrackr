"""
Plot various data like account balance over time

Copyright (c) 2026 Stephanie Johnson
"""

import logging
import yaml
import os, sys
import numpy as np
import matplotlib.pyplot as plt

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
    If rel_to is empty, the balance on the *earliest* date in transactions will be zero.

    Design decision: Balances represent account balance at end of day. Therefore the returned list
    will be one element longer than the input transactions list; the first element will be the balance
    before the first transaction, and the second will be the balance after the first transaction in the
    input.

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
        Account balances as a result of the list of dated transactions.
        If there are multiple transactions per day, there will be multiple balances - 
        not aggregated per day.
    """

    if len(transactions) == 0:
        return []
    
    if len(rel_to) > 1:
        ref_bal = sorted(rel_to, key=lambda r: r[0])[-1] # [date, amount] of chronologically most recent account balance
    elif len(rel_to) == 1:
        ref_bal = rel_to[0]
    else:
        ref_bal = (sorted(transactions, key=lambda t: t[0])[0][0],0.00) # Set balance for first transaction date to zero

    # balances have to be cumulative relative to ref_bal, by date
    transactions.sort(key=lambda a: a[0]) # sort all transactions by date

    earlier_trans = [t for t in transactions if t[0]<=ref_bal[0]] # Balances are for end of day
    if len(earlier_trans) > 0:
        # Add the extra initial balance for the first day:
        earlier_bals = list(zip([earlier_trans[0][0]]+[a[0] for a in earlier_trans[:-1]], reversed(ref_bal[1]-np.cumsum([a[1] for a in reversed(earlier_trans)]))))
    else:
        earlier_bals = []
    
    later_trans = [t for t in transactions if t[0]>ref_bal[0]] 
    if len(later_trans) > 0:
        later_bals = list(zip([a[0] for a in later_trans], np.cumsum([a[1] for a in later_trans])+ref_bal[1]))
    else:
        later_bals = []
    
    if len(earlier_trans) > 0:
        return earlier_bals + [(earlier_trans[-1][0], ref_bal[1])] + later_bals
    else:
        return earlier_bals + later_bals

def plot_balances(all_balances: List[tuple[date, float]], calculated_balances: List[tuple[date, float]]) -> None:
    """
    Plot calculated account balances (from transactions) as well as any stored balances in 
    the same range of dates. Dates are on x, balances are on y
    
    Parameters
    ----------
    all_balances : List[tuple[date, float]]
        Any balances stored in the db. Plotted as red o's for comparison to calculated values.
        Hopefully they match, but there's no guarantee they will (e.g. if some transactions
        are missing from the db)
    calculated_balances : List[tuple[date, float]]
        Account balances calcualted from list of transactions. Plotted as blue .'s   

    Returns
    -------
    None, but a plot is displayed

    """
    
    # Rearrange inputs into tuple of lists
    calc_date, calc_amt = zip(*calculated_balances)
    calculated = (list(calc_date), list(calc_amt))

    input_date, input_amt = zip(*all_balances)
    inputted = (list(input_date), list(input_amt))

    plt.plot(calculated[0], calculated[1], ".b")
    plt.plot(inputted[0], inputted[1], "or", markerfacecolor='none')

    plt.xlabel("Date")
    plt.ylabel("Amount ($)")
    plt.legend(["Balances calculated from transactions","Balances in db"])

    plt.show(block=False) # This makes CI not block

def plot_accnt_balances(accnt_name: str, date_range: List[date], username: str, pw: str) -> None:
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

    plot_balances(all_balances=amts["balances"], calculated_balances=abs_trans)

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("plot_accnt_balances.py takes exactly 5 input args: (1) account name to plot balances of; (2) earliest date; (3) latest date; (4) db username; (5) db pw")

    path_to_config = os.path.join(os.getcwd(), "src", "fintrackr", "config.yml")

    plot_accnt_balances(accnt_name = sys.argv[1], date_range = [sys.argv[2], sys.argv[3]], username = sys.argv[4], pw = sys.argv[5])
