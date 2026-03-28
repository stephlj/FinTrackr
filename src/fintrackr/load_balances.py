# load_balances.py
#
# CLI script to call the utilities in load_data to load balances from csv.
#
# Copyright (c) 2026 Stephanie Johnson

import os, sys
import logging

from fintrackr.utils import DEFAULT_LOGGING_FORMAT
from fintrackr.load_data import load_data_from_CLI

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if len(sys.argv) > 6 or len(sys.argv) < 5:
        raise TypeError("load_data_from_CLI.py takes 4 or 5 input args: (1) account name; (2) path to csv of transactions; (3) db username; (4) db pw (5) [optional] add_account flag")
    
    filepath_base = os.path.split(sys.argv[2])[0]
    logging.basicConfig(filename = os.path.join(filepath_base,"load_balances_log.log"), level="INFO", format=DEFAULT_LOGGING_FORMAT)
    
    if len(sys.argv) == 6:
        load_data_from_CLI(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4], trans=False, add_as_new_acct=True)
    elif len(sys.argv) == 5:
        load_data_from_CLI(accnt_name = sys.argv[1], filepath=sys.argv[2], username = sys.argv[3], pw = sys.argv[4], trans=False, add_as_new_acct=True)