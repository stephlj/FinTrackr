#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import unittest
import subprocess, os
import yaml
import pandas as pd

from fintrackr.init_db import init_db
from fintrackr.add_user import add_user
from fintrackr.fin_db import FinDB

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db, in the process also tests init_db and add_user.
        # TODO later use mocking instead of a real db
        
        path_to_config = os.path.join(os.getcwd(),"tests","data","test_config.yml")
        with open(path_to_config, "r") as config_file:
            config = yaml.safe_load(config_file)
            cls.test_db_name = config["db"]["db_name"]
            cls.test_owner = config["db"]["admin_name"]

        cls.owner_pw = "test_pw"

        init_db(pw=cls.owner_pw, path_to_config=path_to_config)

        cls.user = "test_user"
        cls.user_pw = "pw"
        add_user(name=cls.user, 
                 pw=cls.user_pw, 
                 admin_pw = cls.owner_pw, 
                 path_to_config=path_to_config
        )

        # cls.conn = psycopg.connect(f"dbname={cls.test_db_name} user={cls.user} password={cls.user_pw} host='localhost'")
        cls.FinDB = FinDB(user=cls.user, pw=cls.user_pw, db_name=cls.test_db_name)

    @classmethod
    def tearDownClass(cls):
        cls.FinDB.close()
        # Delete testing db
        exit_code = subprocess.run(["dropdb", cls.test_db_name])
        exit_code2 = subprocess.run(["dropuser",cls.user])
        exit_code3 = subprocess.run(["dropuser",cls.test_owner])

        # We put these at the end to ensure teardown completes even if one of these fails.
        # Note that the @classmethod decorator changes the first arg to the class not
        # an instance of the class, so self.assertEqual fails.
        assert exit_code.returncode==0, "Failed to remove testing db, must now remove manually"
        assert exit_code2.returncode==0, "Failed to remove testing user, must now remove manually"
        assert exit_code3.returncode==0, "Failed to remove testing db owner, must now remove manually"

    def test_execute_query(self):
        # Test cases:
        # - not a SELECT statement (eg, insert)
        # - trying to query a table that doesn't exist in the db
        pass
    
    def test_load_transactions(self):
        path_to_test_transactions = os.path.join(os.getcwd(),"tests","data","test_data_cc.csv")
        transactions_to_add = pd.read_csv(path_to_test_transactions, header=None)

        # load_transactions adds rows to a staging table that should be empty at start
        num_rows_added = self.FinDB.load_transactions(path_to_transactions=path_to_test_transactions)
        assert num_rows_added == transactions_to_add.shape[0], "Rows added to staging table does not match file"

        path_to_too_many_columns = os.path.join(os.getcwd(),"tests","data","test_data_cc_wrongnumcols.csv")
        num_rows_added = self.FinDB.load_transactions(path_to_transactions=path_to_too_many_columns)
        assert num_rows_added == 0, "No rows should have been added, malformed input"

        # TODO test wrongtype - but that should go in BLL test anyway
    
    def test_add_transactions(self):
    #     # Will test add_transactions method TODO
         pass
