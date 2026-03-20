"""
Utility to load a set of transactions from a csv into the db, via the command line.

Copyright (c) 2026 Stephanie Johnson
"""

import sys
import yaml
import logging

import fintrackr.fin_db
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH, Col_Def
from fintrackr.io import check_csv_format

logger = logging.getLogger(__name__)

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

    # Check input first
    transactions_cols = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]

    new_path = check_csv_format(filepath=filepath, cols=transactions_cols)

    if len(new_path) != 0:
        # Switch to modified file with corrected format
        filepath = new_path

    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)

    result = FinDB.add_transactions(
            path_to_source_file = filepath, 
            source_info = accnt_name
            )

    if result == 1:
        logger.info(f"Successfully logged transactions from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log transactions from file {filepath} in {db_name} under account {accnt_name}")

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("load_transactions_from_CLI.py takes exactly 4 input args: (1) account name; (2) path to csv of transactions; (3) db username; (4) db pw")

    load_transctions_from_CLI(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4])

