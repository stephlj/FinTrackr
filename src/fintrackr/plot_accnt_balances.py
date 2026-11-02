"""
Plot various data like account balance over time

Copyright (c) 2026 Stephanie Johnson
"""

import logging
import yaml
import sys
import numpy as np
import matplotlib.pyplot as plt

from typing import List
from datetime import date
from decimal import Decimal

from fintrackr.fin_db import FinDB
from fintrackr.fin_dataclasses import Transaction, Balance
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH

logger = logging.getLogger(__name__)


def relative_bal_by_date(references: List[Balance], transactions: List[Transaction]) -> List[Transaction]:
    """
    Return a list of Transactions calculated relative to the amount on date in reference balance.
    If references is a List of len>1, uses the chronologically *most recent* account balance.
    If references is empty, the balance on the *earliest* date in transactions will be zero.

    Design decision: Balances represent account balance at end of day. Therefore depending on the dates
    in references vs transactions, the returned list may be one element longer than the input transactions list; 
    the first element may be the balance before the first transaction, and the second would then be the 
    balance after the first transaction in the input.

    Parameters
    ----------
    references : List[Balance]
        Calculate all balances relative to the amount for the most recent date
    transactions : List[Transactions]
        Calculate account balance as a result of each transaction in this list
    
    Return
    ------
    List[Transaction]
        Account balances as a result of the list of dated transactions.
        If there are multiple transactions per day, there will be multiple balances - 
        not aggregated per day.
        Returning a list of Transactions, rather than Balances, so that I can include the description associated 
        with each transaction (e.g. for plotting later).
    """

    if len(transactions) == 0:
        return []
    
    # Set a single absolute account balance on a date, which all subsequent balances will be relative to
    if len(references) >= 1:
        ref = sorted(references, key=lambda r: r.balance_date)[-1] # [date, amount] of chronologically most recent account balance
    else:
        ref = Balance(balance_date=sorted(transactions, key=lambda t: t.posted_date)[0].posted_date, amount = Decimal('0.00')) # Set balance for first transaction date to zero

    # balances have to be cumulative relative to ref_bal, by date
    transactions.sort(key=lambda a: a.posted_date)

    earlier_trans = [t for t in transactions if t.posted_date<=ref.balance_date] # Balances are for end of day
    if len(earlier_trans) > 0:
        # Add the extra initial balance for the first day:
        earlier_bals_tuple = list(zip([earlier_trans[0].posted_date]+[a.posted_date for a in earlier_trans[:-1]], reversed(ref.amount-np.cumsum([a.amount for a in reversed(earlier_trans)])), ["Reference"]+[c.description for c in earlier_trans]))
        earlier_bals = [Transaction(posted_date=d, amount=a, description=c) for d, a, c in earlier_bals_tuple]
    else:
        earlier_bals = []
    
    later_trans = [t for t in transactions if t.posted_date>ref.balance_date] 
    if len(later_trans) > 0:
        later_bals_tuple = list(zip([a.posted_date for a in later_trans], np.cumsum([a.amount for a in later_trans])+ref.amount, [c.description for c in later_trans]))
        later_bals = [Transaction(posted_date=d, amount=a, description=c) for d, a, c in later_bals_tuple]
    else:
        later_bals = []
    
    if len(earlier_trans) > 0:
        return earlier_bals + [Transaction(posted_date=earlier_trans[-1].posted_date, amount=ref.amount, description="Reference")] + later_bals
    else:
        return earlier_bals + later_bals

def plot_balances(all_balances: List[Balance], calculated_balances: List[Transaction]) -> None:
    """
    Plot calculated account balances (from transactions) as well as any stored balances in 
    the same range of dates. Dates are on x, balances are on y
    
    Parameters
    ----------
    all_balances : List[Balance]
        Any balances stored in the db. Plotted as red o's for comparison to calculated values.
        Hopefully they match, but there's no guarantee they will (e.g. if some transactions
        are missing from the db)
    calculated_balances : List[Transaction]
        Account balances calcualted from list of transactions. Plotted as blue .'s   

    Returns
    -------
    None, but a plot is displayed

    """
    
    # Rearrange inputs into tuple of lists
    calc_date, calc_amt, descriptions = zip(*calculated_balances)
    calculated = (list(calc_date), list(calc_amt))

    input_date, input_amt = zip(*all_balances)
    inputted = (list(input_date), list(input_amt))

    plt.plot(calculated[0], calculated[1], ".b")
    plt.plot(inputted[0], inputted[1], "or", markerfacecolor='none')

    plt.xlabel("Date")
    plt.ylabel("Amount ($)")
    plt.legend(["Balances calculated from transactions","Balances in db"])

    plt.show(block=False) # This makes CI not block

def plot_accnt_balances(accnt_name: str, date_range: List[date], username: str, pw: str, db_config: str = '') -> None:
    """
    Plot specified account data within date range.
    If no point-in-time account balance is saved in the db, 
    balances will be relative to the first date in the date range.
    If there are multiple balances in date range, balances will be
    relative to the most recent; and the rest will be plotted for references.

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
    db_config : str, optional
        path to config file for db.
        Will use default in utils if not specified.

    Returns
    -------
    None, but a plot is displayed
    """

    if db_config=='':
        db_config = CONFIG_PATH

    with open(db_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]

    with FinDB(user=username, pw=pw, db_name=db_name) as db_conn:
        balances = db_conn.get_balances_in_date_range(accnt_name=accnt_name, date_range=date_range)  
        transactions = db_conn.get_transactions_in_date_range(accnt_name=accnt_name, date_range=date_range)

    abs_trans = relative_bal_by_date(references = balances, transactions = transactions)

    plot_balances(all_balances=balances, calculated_balances=abs_trans)

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("plot_accnt_balances.py takes exactly 5 input args: (1) account name to plot balances of; (2) earliest date; (3) latest date; (4) db username; (5) db pw")

    plot_accnt_balances(accnt_name = sys.argv[1], date_range = [sys.argv[2], sys.argv[3]], username = sys.argv[4], pw = sys.argv[5])
