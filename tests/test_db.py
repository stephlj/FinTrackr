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
        cls.element_to_match = str(cls.transactions_to_add.iloc[1,1])
        cls.element_to_match = cls.element_to_match[0] + "$" + cls.element_to_match[1:] + "0"

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
    
    def test_load_transactions(self):
        # Also does an implicit test of select_from_table

        # load_transactions adds rows to a staging table that should be empty at start
        num_rows_added = self.FinDB.load_transactions(path_to_transactions=self.path_to_test_transactions)
        self.assertEqual(num_rows_added, self.transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(self.element_to_match, 
                         self.FinDB.select_from_table(table_name="staging", col_names=("amount"), subset_col="description", subset_val='Concert tickets')[0][0], 
                         "Data were scrambled when copied into staging"
                         )
        
        # test that staging has NOT been cleared at this point
        self.assertEqual(len(self.FinDB.select_from_table(table_name="staging", col_names=("posted_date", "amount", "description"))), self.transactions_to_add.shape[0], "Staging table didn't persist")

        # test that it does clear if we try to add new transactions
        num_rows_added = self.FinDB.load_transactions(path_to_transactions=self.path_to_test_transactions)
        self.assertEqual(num_rows_added, self.transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(len(self.FinDB.select_from_table(table_name="staging", col_names=("posted_date", "amount", "description"))), self.transactions_to_add.shape[0], "Staging table wasn't cleared")

        # This should go in the BLL test section
        # path_to_too_many_columns = os.path.join(os.getcwd(),"tests","data","test_data_cc_wrongnumcols.csv")
        # num_rows_added_2 = self.FinDB.load_transactions(path_to_transactions=path_to_too_many_columns)
        # self.assertEqual(num_rows_added_2, 0, "No rows should have been added, malformed input")
        
    
    # def test_add_transactions(self):
    #     # Add_transactions calls load_transactions (which we test separately above)

    #     num_transactions_added = self.FinDB.add_transactions(
    #         path_to_source_file = self.path_to_test_transactions, 
    #         source_info = self.source_info
    #         )
    #     self.assertEqual(num_transactions_added, self.transactions_to_add.shape[0], "Number of added transactions does not match file")
    #     # TODO spot check some values in the transactions table. Maybe move logic picking a transaction to setup since it's used here and in test_load_transactions

    #     # TODO additional test for what happens when duplicates are attempted to add
    #     # TODO test for trying to load an empty file, or use the wrong-number-columns file so staging should be empty