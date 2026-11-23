# One-time initialization of the database.
#
# Copyright (c) 2026 Stephanie Johnson

import sys
import logging

from dbcommons.init_db import init_db

from fintrackr.utils import DEFAULT_LOGGING_FORMAT, CONFIG_PATH, SCHEMA_PATH

def fin_init(admin_pw: str, path_to_config: str=CONFIG_PATH)->None:
    init_db(pw=admin_pw,path_to_config=path_to_config, path_to_schema=SCHEMA_PATH)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    if len(sys.argv) != 2:
        raise ValueError("fin_init takes only one arg: owner pw")
    
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
    
    fin_init(admin_pw=sys.argv[1])