"""
Utility to load data (balances or transactions) from a csv into the db, via the command line.

Copyright (c) 2026 Stephanie Johnson
"""

import sys
import yaml
import logging
import pandas as pd

from datetime import date
from decimal import Decimal
from math import ceil

import fintrackr.fin_db
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH, Col_Def
from fintrackr.io import check_csv_format, strip_header

BALS_STAGING_COLS = [Col_Def(col_name="date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
    ]

TRANS_STAGING_COLS = [Col_Def(col_name="posted_date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
            Col_Def(col_name="description", col_type="text")
    ]

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

    num_staged_balances = FinDB.csv_to_staging(csv_path=path_to_balances, csv_columns=BALS_STAGING_COLS)

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

def add_transactions(FinDB: object, path_to_source_file: str, source_info: str) -> None:
    """
    Load transactions from a file and log the addition of these transactions
    in the data_load_metadata table.

    Only new transactions are added; duplicates (which have identity across the 3
    input columns of Date, Amount, and Description with an existing transaction row)
    are ignored.

    Parameters
    ----------
    FinDB: object
        FinDB object that manages db access.
    path_to_source_file: str
        Path to a csv where every row is a transaction.
    source_info: str
        Are these transactions from credit card, checking account, etc
        This is the "name" field in the data_sources table.
        It will be added if it doesn't already exist.

    Returns
    -------
    int
        Number of transactions added.
    """

    num_new_transactions = 0

    num_staged_transactions = FinDB.csv_to_staging(csv_path=path_to_source_file, csv_columns=TRANS_STAGING_COLS)

    if num_staged_transactions == 0:
        logger.info("No transactions loaded from source file to staging table; no transactions will be added")
        return num_new_transactions
    
    # Get id for this source_info or add if it doesn't exist
    source_info_id = FinDB.add_data_source(source_info)

    today_date = date.today()
    
    transactions_query = "WITH joined AS ( " \
        "    SELECT s.* " \
        "    FROM staging s " \
        "    LEFT JOIN transactions t ON " \
        "        t.posted_date = s.posted_date AND " \
        "        t.amount = s.amount AND " \
        "        t.description = s.description " \
        "    WHERE t.id IS NULL " \
        "), " \
        "meta AS ( " \
        "    INSERT INTO data_load_metadata " \
        "        (date_added, username, source, data_source_id) " \
        "    VALUES (%s, %s, %s, %s)" \
        "    " \
        "    RETURNING id " \
        ") " \
        "INSERT INTO transactions (posted_date, amount, description, metadatum_id) " \
        "SELECT posted_date, amount, description, meta.id " \
        "FROM joined, meta " \
        "RETURNING *;"
        
    try:
        all_new_transactions = FinDB.execute_query(transactions_query, (today_date, FinDB.user, path_to_source_file, source_info_id))
    except Exception as e:
        logger.exception(f"Insertion into transactions table failed with exception: {e}; return from query: {num_new_transactions}")
        raise ValueError(f"Insertion into transactions table failed with exception: {e}")
    
    if all_new_transactions is None:
        logger.error("No transactions inserted")
        # Check if all new transactions to load are already in db and that's why it failed:
        check_dups = "SELECT s.* " \
            "    FROM staging s " \
            "    LEFT JOIN transactions t ON " \
            "        t.posted_date = s.posted_date AND " \
            "        t.amount = s.amount AND " \
            "        t.description = s.description " \
            "    WHERE t.id IS NULL;"
        if len(FinDB.execute_query(check_dups)) == 0:
            logger.error("All staged transactions are already in transactions table")
            return 0
        else:
            raise ValueError("No transactions inserted, but not because all new transactions were in db already")

    # Drop staging table
    FinDB.execute_action("DROP TABLE staging;")

    return len(all_new_transactions)

def load_data_from_CLI(accnt_name: str, filepath: str, username: str, pw: str, db_config: str = '') -> None:
    """
    
    Load transactions or balances from csv file into db.

    Parameters
    ----------
    accnt_name : str
        Which account are these balances or transactions for?
        Equivalent to name column in data_sources (will be added if doesn't exist in that table)
    filepath : str
        Path to a csv file to load.
    username : str
        User to use to connect to db
    pw : str
        User's pw to connect to db
    db_config : str, optional
        path to config file for db.
        Will use default in utils if not specified.

    Returns
    -------
    None
    """
    
    if db_config=='':
        db_config = CONFIG_PATH

    with open(db_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        date_headers = config["input_files"]["date_header"]
        amount_headers = config["input_files"]["amount_header"]
        desc_headers = config["input_files"]["description_header"]

    # Are these balances or transactions?
    # Determine based on whether they're mostly negative or mostly positive numbers
    # (Mostly neg is transactions)
    # TODO refactor so I'm not loading the file here and in check_csv_format
    temp_df = pd.read_csv(filepath, header=None)
    temp_df, _ = strip_header(temp_df)
    amts_col = temp_df.iloc[:,[str(x)=='float64' for x in temp_df.dtypes]]
    if amts_col.shape[1] != 1:
        logger.error("Could not identify amounts column from which to infer balances vs transactions from file {filepath}")
        raise ValueError("Could not identify amounts column from which to infer balances vs transactions from file {filepath}")
    num_neg = len(amts_col[amts_col.squeeze()<0])
    if num_neg >= ceil(len(amts_col)):
        trans=True
    else:
        trans=False

    # Clean input if necessary
    # Enumerate all possible input column combos:
    expect_cols = []
    for d in date_headers:
        for a in amount_headers:
            for c in desc_headers:
                # Note order matters here!
                # check_csv_format will reorder columns to match this spec.
                # So this spec must match the order expected when csv contents
                # are loaded into the staging table in csv_to_staging().
                # That order is in *_STAGING_COLS at top.
                # TODO Derive col order from *_STAGING_COLS
                if trans:
                    expect_cols.append([Col_Def(col_name=d, col_type="date"),
                                    Col_Def(col_name=a, col_type="money"),
                                    Col_Def(col_name=c, col_type="text")
                            ])
                else:
                    expect_cols.append([Col_Def(col_name=d, col_type="date"),
                            Col_Def(col_name=a, col_type="money"),
                            ])
    
    success = False
    for c in expect_cols:
        try:
            new_path = check_csv_format(filepath=filepath, cols=c)
            success = True
        except:
            pass
        if success:
            break

    if not success:
        logger.error("Unable to load data from file {filepath}")
        raise ValueError("Unable to load data from file {filepath}")

    if len(new_path) != 0:
        # Switch to modified file with corrected format
        filepath = new_path

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)
    
    if trans:
        result = add_transactions(
                FinDB = FinDB,
                path_to_source_file = filepath, 
                source_info = accnt_name
                )
    else:
        result = add_balances_from_csv(
            FinDB=FinDB, 
            accnt = accnt_name, 
            path_to_balances=filepath
            )

    FinDB.close()

    if result >= 1:
        logger.info(f"Successfully logged data from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log data from file {filepath} in {db_name} under account {accnt_name}")

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("load_data_from_CLI.py takes exactly 4 input args: (1) account name; (2) path to csv of transactions; (3) db username; (4) db pw")

    load_data_from_CLI(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4])

