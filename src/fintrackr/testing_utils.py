"""
Extracting some commonly used code for testing (manual and automated).
"""

import os
import yaml

from fintrackr.init_db import init_db
from fintrackr.add_user import add_user
import fintrackr.fin_db

CONFIG_PATH = os.path.join(os.getcwd(),"tests","data","test_config.yml")
TEST_TRANSACTIONS_PATH = os.path.join(os.getcwd(),"tests","data","test_data_cc.csv")

def config_params() -> dict:
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        test_db_name = config["db"]["db_name"]
        test_owner = config["db"]["admin_name"]

    return {
        "test_db_name" : test_db_name,
        "test_owner": test_owner,
        "owner_pw": "test_pw",
        "user": "test_user",
        "user_pw" :"pw"
    }

def set_up_test_DB(params: dict) -> None:
    """
    If testing manually, run this in the terminal afterwards to clean up:
        dropdb test_fin_db
        dropuser test_user
        dropuser test_admin

    Parameters
    ----------
    params : dict
        Output of config_params
    """

    init_db(pw=params["owner_pw"], path_to_config=CONFIG_PATH)

    add_user(name=params["user"], 
                pw=params["user_pw"], 
                admin_pw = params["owner_pw"], 
                path_to_config=CONFIG_PATH
    )

    FinDB = fintrackr.fin_db.FinDB(user=params["user"], pw=params["user_pw"], db_name=params["test_db_name"])

    return FinDB