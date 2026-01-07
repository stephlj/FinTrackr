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

        cls.FinDB = FinDB(user=cls.user, pw=cls.user_pw, db_name=cls.test_db_name)

        # Some test fixtures shared by multiple tests:
        cls.path_to_test_transactions = os.path.join(os.getcwd(),"tests","data","test_data_cc.csv")
        cls.transactions_to_add = pd.read_csv(cls.path_to_test_transactions, header=None)
        cls.source_info = "cc"

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
        # - trying to query a table that doesn't exist in the db
        pass
    
    def test_load_transactions(self):
        # Also contains an implicit test for execute_query which is not ideal ... 

        # load_transactions adds rows to a staging table that should be empty at start
        num_rows_added = self.FinDB.load_transactions(path_to_transactions=self.path_to_test_transactions)
        self.assertEqual(num_rows_added, self.transactions_to_add.shape[0], "Rows added to staging table does not match file")
        element_to_match = str(self.transactions_to_add.iloc[1,1])
        element_to_match = element_to_match[0] + "$" + element_to_match[1:] + "0"
        self.assertEqual(element_to_match, 
                         self.FinDB.execute_query(f"SELECT amount FROM staging WHERE description='Concert tickets';")[0][0], 
                         "Data were scrambled when copied into staging"
                         )

        path_to_too_many_columns = os.path.join(os.getcwd(),"tests","data","test_data_cc_wrongnumcols.csv")
        num_rows_added_2 = self.FinDB.load_transactions(path_to_transactions=path_to_too_many_columns)
        self.assertEqual(num_rows_added_2, 0, "No rows should have been added, malformed input")

        # TODO test wrongtype - but that should go in BLL test anyway
    
    def test_add_transactions(self):
        # Add_transactions calls load_transactions (which we test separately above)
         
        # Staging will already contain the contents of this file:
        # TODO what happens when I re-call load_transactions?
        num_transactions_added = self.FinDb.add_transactions(
            path_to_source_file = self.path_to_test_transactions, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, self.transactions_to_add.shape[0], "Not all transactions were added")

        # TODO additional test for what happens when duplicates are attempted to add