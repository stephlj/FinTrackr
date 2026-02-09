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

from datetime import date

import fintrackr.testing_utils as utils

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db, in the process also tests init_db and add_user.
        # TODO later use mocking instead of a real db
        
        cls.params = utils.config_params()

        cls.FinDB = utils.set_up_test_DB(params=cls.params)

        # Some test fixtures shared by multiple tests:
        cls.path_to_test_transactions = utils.TEST_TRANSACTIONS_PATH
        cls.transactions_to_add = pd.read_csv(cls.path_to_test_transactions, header=None)
        cls.element_to_match = str(cls.transactions_to_add.iloc[1,1])
        cls.element_to_match = cls.element_to_match[0] + "$" + cls.element_to_match[1:] + "0"

        cls.source_info = "cc"
        cls.balance_date = date(year=2025, month=9, day=9)
        cls.balance_amount = 5000.00

    @classmethod
    def tearDownClass(cls):
        cls.FinDB.close()
        # Delete testing db
        exit_code = subprocess.run(["dropdb", cls.params["test_db_name"]])
        exit_code2 = subprocess.run(["dropuser",cls.params["user"]])
        exit_code3 = subprocess.run(["dropuser",cls.params["test_owner"]])

        # We put these at the end to ensure teardown completes even if one of these fails.
        # Note that the @classmethod decorator changes the first arg to the class not
        # an instance of the class, so self.assertEqual fails.
        assert exit_code.returncode==0, "Failed to remove testing db, must now remove manually"
        assert exit_code2.returncode==0, "Failed to remove testing user, must now remove manually"
        assert exit_code3.returncode==0, "Failed to remove testing db owner, must now remove manually"
    
    def test_add_balance(self):
        # does-it-run test
        self.assertEqual(self.FinDB.add_balance(
                            accnt=self.source_info,
                            bal_date=self.balance_date,
                            bal_amt=self.balance_amount
                            ), 
                        1)
    
    def test_stage_transactions(self):
        # stage_transactions adds rows to a staging table that should be empty at start
        num_rows_added = self.FinDB.stage_transactions(path_to_transactions=self.path_to_test_transactions)
        self.assertEqual(num_rows_added, self.transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(self.element_to_match, 
                         self.FinDB.execute_query("SELECT amount FROM staging WHERE description=%s;", ('Concert tickets',))[0][0], 
                         "Data were scrambled when copied into staging"
                         )
        
        # test that staging has NOT been cleared at this point
        self.assertEqual(len(self.FinDB.execute_query("SELECT posted_date, amount, description FROM staging;")), self.transactions_to_add.shape[0], "Staging table didn't persist")

        # test that it does clear if we try to add new transactions
        num_rows_added = self.FinDB.stage_transactions(path_to_transactions=self.path_to_test_transactions)
        self.assertEqual(num_rows_added, self.transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(len(self.FinDB.execute_query("SELECT posted_date, amount, description FROM staging;")), self.transactions_to_add.shape[0], "Staging table wasn't cleared")

        # This should go in the BLL test section
        # path_to_too_many_columns = os.path.join(os.getcwd(),"tests","data","test_data_cc_wrongnumcols.csv")
        # num_rows_added_2 = self.FinDB.stage_transactions(path_to_transactions=path_to_too_many_columns)
        # self.assertEqual(num_rows_added_2, 0, "No rows should have been added, malformed input")
        
    
    def test_add_transactions(self):
        # Add_transactions calls stage_transactions (which we test separately above)

        num_transactions_added = self.FinDB.add_transactions(
            path_to_source_file = self.path_to_test_transactions, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, self.transactions_to_add.shape[0], "Number of added transactions does not match file")
        self.assertEqual(self.element_to_match, 
                         self.FinDB.execute_query("SELECT amount FROM transactions WHERE description=%s;",('Concert tickets',))[0][0], 
                         "Data were scrambled when loaded into transactions"
                         )
        
        # Test that trying to upload the same file again fails
        # (it actually errors out with a silent error, unfortunately: raises "Key (source)=(/Users/steph/Documents/Code/FinTrackr/tests/data/test_data_cc.csv) already exists)")
        num_transactions_added = self.FinDB.add_transactions(
            path_to_source_file = self.path_to_test_transactions, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, 0, "Duplicates should not have been successfully loaded")

        # Test what happens when partial duplicates are added
        additional_transactions_path = os.path.join(os.getcwd(),"tests","data","test_data_checking.csv")
        addtl_trans = pd.read_csv(additional_transactions_path, header=None)
        num_new_trans = len(addtl_trans)
        dup_trans = self.transactions_to_add.loc[self.transactions_to_add.iloc[:,2]=="Safeway"]
        addtl_trans = pd.concat([addtl_trans, dup_trans])

        num_transactions_added = self.FinDB.add_transactions(
            path_to_source_file = additional_transactions_path, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, num_new_trans, "Duplicates should not have been successfully loaded")

    def test_data_from_date_range(self):
        # pytest runs each test case independently, so re-set-up the db
        # Neither of these functions allow duplicates

        self.FinDB.add_balance(
            accnt=self.source_info,
            bal_date=self.balance_date,
            bal_amt=self.balance_amount
        )
        self.FinDB.add_transactions(
            path_to_source_file = self.path_to_test_transactions, 
            source_info = self.source_info
        )

        print(self.FinDB.execute_query("SELECT * FROM transactions;"))

        amts = self.FinDB.data_from_date_range(
            data_source = self.source_info, 
            date_range = ['9/5/2025','9/10/2025']
        )

        bal_money = "$"+f"{self.balance_amount}"[0]+","+f"{self.balance_amount}"[1:]+"0"
        self.assertEqual(amts["balances"][0][1], bal_money, "data_from_date_range did not return correct balance amount")

        self.assertEqual(len(amts["transactions"]), 3, "data_from_date_range did not return the correct number of transactions") # assumes BETWEEN is inclusive


