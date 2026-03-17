"""
Utility to load a set of account balances on particular dates from a csv into the db.

Copyright (c) 2026 Stephanie Johnson
"""

import sys
import yaml
import logging

from datetime import date

import fintrackr.fin_db
from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH

logger = logging.getLogger(__name__)

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

    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]

    # TODO add some input handling around the file? (check columns? extract into a util?)

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)

    result = FinDB.add_balances_from_csv(accnt = accnt_name, path_to_balances=filepath)

    if result == 1:
        logger.info(f"Successfully logged balances from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log balances of from file {filepath} in {db_name} under account {accnt_name}")

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    if len(sys.argv) != 6:
        raise TypeError("load_balances.py takes exactly 4 input args: (1) account name; (2) path to csv of balances; (3) db username; (4) db pw")

    load_balances(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4])

