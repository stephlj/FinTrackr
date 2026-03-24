"""
Utility to load a set of transactions from a csv into the db, via the command line.

Copyright (c) 2026 Stephanie Johnson
"""

import sys
import yaml
import logging

from datetime import date

import fintrackr.fin_db
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH, Col_Def
from fintrackr.io import check_csv_format

STAGING_COLS = [Col_Def(col_name="posted_date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
            Col_Def(col_name="description", col_type="text")
    ]

logger = logging.getLogger(__name__)

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

    num_staged_transactions = FinDB.csv_to_staging(csv_path=path_to_source_file, csv_columns=STAGING_COLS)

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

def load_transctions_from_CLI(accnt_name: str, filepath: str, username: str, pw: str) -> None:
    """
    
    Load transactions from csv file into db. Uses the db name in config file.

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

    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        date_headers = config["input_files"]["date_header"]
        amount_headers = config["input_files"]["amount_header"]
        desc_headers = config["input_files"]["description_header"]

    # Check input first
    # Enumerate all possible input column combos:
    success = False
    for d in date_headers:
        for a in amount_headers:
            for c in desc_headers:
                try:
                    # Note order matters here!
                    # check_csv_format will reorder columns to match this spec.
                    # So this spec must match the order expected when csv contents
                    # are loaded into the staging table in csv_to_staging().
                    # That order is in STAGING_COLS at top.
                    # TODO Derive balances_cols from STAGING_COLS
                    transactions_cols = [Col_Def(col_name=d, col_type="date"),
                                Col_Def(col_name=a, col_type="money"),
                                Col_Def(col_name=c, col_type="text")
                        ]
                    new_path = check_csv_format(filepath=filepath, cols=transactions_cols)
                    success = True
                except:
                    pass
    if not success:
        logger.error("Unable to load transactions from file {filepath}")
        raise ValueError("Unable to load transactions from file {filepath}")

    if len(new_path) != 0:
        # Switch to modified file with corrected format
        filepath = new_path

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)

    result = add_transactions(
            FinDB = FinDB,
            path_to_source_file = filepath, 
            source_info = accnt_name
            )
    FinDB.close()

    if result == 1:
        logger.info(f"Successfully logged transactions from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log transactions from file {filepath} in {db_name} under account {accnt_name}")

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("load_transactions_from_CLI.py takes exactly 4 input args: (1) account name; (2) path to csv of transactions; (3) db username; (4) db pw")

    load_transctions_from_CLI(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4])

