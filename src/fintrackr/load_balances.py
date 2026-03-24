"""
Utility to load a set of account balances on particular dates from a csv into the db.

Copyright (c) 2026 Stephanie Johnson
"""

import sys
import yaml
import logging

from datetime import date
from decimal import Decimal

import fintrackr.fin_db
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH, Col_Def
from fintrackr.io import check_csv_format

logger = logging.getLogger(__name__)

def add_balance(FinDB: object, accnt: str, bal_date: date, bal_amt: str) -> int:
    """
    Log a balance in the db. Will not allow exact duplicates to be added.

    Parameters
    ----------
    FinDB : object
        FinDB object for db access
    accnt: str
        Must exist in data_sources table as a name.
    bal_date : datetime.date
        Date that this was the account's balance.
    bal_amt : str
        Account balance on balance_date
    
    Return
    ------
    int, success (1) or not (0)
    """

    # Make sure bal_amt is formatted so it's recognized as money
    bal_amt = str(Decimal(bal_amt).quantize(Decimal('0.01')))

    accnt_id = FinDB.add_data_source(source_name=accnt)

    try:
        rows_added = FinDB.execute_query("INSERT INTO balances (accnt_id, date, amount) VALUES (%s, %s, %s) RETURNING *;", (accnt_id, bal_date, bal_amt))
    except Exception as e:
        logger.exception(f"Insertion into balances table failed with exception: {e}; return from query: {rows_added}")
        raise ValueError(f"Insertion into balances table failed with exception: {e}")
    
    if rows_added is not None:
        if len(rows_added) == 1:
            return 1
        else:
            logger.exception("Insertion into balances table returned something unexpected: {rows_added}")
            raise ValueError("Insertion into balances table returned something unexpected: {rows_added}")
    else:
        logger.info(f"No rows added to balances table; balance of {bal_amt} on date {bal_date} for account {accnt_id} may already exist")
        return 0
    
def add_balances_from_csv(FinDB: object, accnt: str, path_to_balances: str) -> int:
    """
    Load balances from csv into db.
    Will not allow duplicates to be added.

    Parameters
    ----------
    FinDB : object
        FinDB object for db access
    accnt: str
        Must exist in data_sources table as a name.
    path_to_balances : str
        Filepath to csv to load.
        Columns must be Date, Amount (in that order)
    
    Return
    ------
    int
        Number of balances added
    """        

    num_new_balances = 0

    # Get id for this source_info or add if it doesn't exist
    accnt_id = FinDB.add_data_source(source_name=accnt)

    staging_cols = [Col_Def(col_name="date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
    ]

    num_staged_balances = FinDB.csv_to_staging(csv_path=path_to_balances, csv_columns=staging_cols)

    if num_staged_balances == 0:
        logger.info("No balances loaded from source file to staging table; no balances will be added to db")
        return num_new_balances
    
    balances_query = "INSERT INTO balances (date, amount, accnt_id) " \
        "SELECT date, amount, %s " \
        "FROM staging " \
        "RETURNING *;"
    
    try:
        all_new_balances = FinDB.execute_query(balances_query, (accnt_id,))
    except Exception as e:
        logger.exception(f"Insertion into balances table failed with exception: {e}; return from query: {all_new_balances}")
        raise ValueError(f"Insertion into balances table failed with exception: {e}")
    
    FinDB.execute_action("DROP TABLE staging;")
    
    if all_new_balances is not None:
        return len(all_new_balances)
    else:
        logger.info(f"No rows added to balances table; all balances in file {path_to_balances} may be in db")
        return 0

def load_balances(accnt_name: str, filepath: str, username: str, pw: str) -> None:
    """
    
    Load balances from csv file into db. Uses the db name in config file.

    Parameters
    ----------
    accnt_name : str
        Which account are these balances for?
        Equivalent to name column in data_sources (will be added if doesn't exist in that table)
    filepath : str
        Path to a csv file to load.
        Columns must be Date, Amount
    username : str
        User to use to connect to db
    pw : str
        User's pw to connect to db

    Returns
    -------
    None
    """

    # Check input first
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        date_headers = config["input_files"]["date_header"]
        amount_headers = config["input_files"]["amount_header"]
    
    success = False
    for d in date_headers:
        for a in amount_headers:
            try:
                # Note order matters here!
                # check_csv_format will reorder columns to match this spec.
                # So this spec must match the order expected when csv contents
                # are loaded into the staging table in csv_to_staging().
                balances_cols = [Col_Def(col_name=d, col_type="date"),
                            Col_Def(col_name=a, col_type="money"),
                    ]
                new_path = check_csv_format(filepath=filepath, cols=balances_cols)
                success = True
            except:
                pass
    if not success:
        logger.error("Unable to load balances from file {filepath}")
        raise ValueError("Unable to load balances from file {filepath}")

    if len(new_path) != 0:
        # Switch to modified file with corrected format
        filepath = new_path

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)

    result = add_balances_from_csv(FinDB=FinDB, accnt = accnt_name, path_to_balances=filepath)
    FinDB.close()

    if result == 1:
        logger.info(f"Successfully logged balances from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log balances from file {filepath} in {db_name} under account {accnt_name}")

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("load_balances.py takes exactly 4 input args: (1) account name; (2) path to csv of balances; (3) db username; (4) db pw")

    load_balances(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4])

