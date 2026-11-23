# load_transactions.py
#
# CLI script to call the utilities in load_data to load balances from csv.
#
# Copyright (c) 2026 Stephanie Johnson

import os, sys
import logging

from fintrackr.utils import DEFAULT_LOGGING_FORMAT
from fintrackr.load_data import DataLoader
from fintrackr.utils import CONFIG_PATH

if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    if len(sys.argv) != 5:
        raise TypeError("load_transactions takes exactly 4 input args: (1) account name; (2) path to csv of transactions; (3) db username; (4) db pw")

    filepath_base = os.path.split(sys.argv[2])[0]
    logging.basicConfig(filename = os.path.join(filepath_base,"load_transactions_log.log"), level="INFO", format=DEFAULT_LOGGING_FORMAT)
    
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    with DataLoader(user=sys.argv[3], pw = sys.argv[4]) as dl:
        dl.add_transactions_from_csv(path_to_csv=sys.argv[2], account_name= sys.argv[1], config_path=CONFIG_PATH)