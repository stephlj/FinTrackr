# CLI script to add a new account to the db.
#
# Copyright (c) 2026 Stephanie Johnson

import sys
import logging
import yaml

from fintrackr.utils import DEFAULT_LOGGING_FORMAT
from fintrackr.fin_db import FinDB
from fintrackr.utils import CONFIG_PATH


if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    if len(sys.argv) != 4:
        raise TypeError("add_account takes exactly 3 input args: (1) name of account to add; (2) db username; (3) db pw")

    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]

    with FinDB(user=sys.argv[2],pw=sys.argv[3],db_name=db_name) as dbconn:
        dbconn.add_data_source(source_name=sys.argv[1])

    logger.info(f"Added {sys.argv[1]} as an account in database {db_name}")