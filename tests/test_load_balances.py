# test_load_balances.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import subprocess, os
import pandas as pd

from datetime import date

import fintrackr.load_balances
import fintrackr.testing_utils as utils

class TestLoadBalances(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = utils.config_params()
        cls.FinDB = utils.set_up_test_DB(params=cls.params)

        # Shared by multiple tests
        cls.source_info = "cc"
        cls.balance_date = date(year=2025, month=9, day=9)
        cls.balance_amount = 5000.00

        cls.input_path = os.path.join(utils.TEST_DATA_PATH,"test_balances.csv")

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
        self.assertEqual(fintrackr.load_balances.add_balance(
                            FinDB = self.FinDB,
                            accnt=self.source_info,
                            bal_date=self.balance_date,
                            bal_amt=self.balance_amount
                            ), 
                        1)
        
        # Does it exit gracefully if an attempt to add the same balance again is made
        self.assertEqual(fintrackr.load_balances.add_balance(
                            FinDB = self.FinDB,
                            accnt=self.source_info,
                            bal_date=self.balance_date,
                            bal_amt=self.balance_amount
                            ),
                         0)
    
    def test_add_balances_from_csv(self):        
        
        balances_to_add = pd.read_csv(self.input_path, header=None)

        num_balances_added = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB, 
                                    accnt = self.source_info, 
                                    path_to_balances = self.input_path
                                    )
        self.assertEqual(num_balances_added, balances_to_add.shape[0], "Number of added balances does not match file")
        
        # Check we can't add the same balances again:
        num_balances_added2 = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB,
                                    accnt = self.source_info, 
                                    path_to_balances = self.input_path
                                    )
        self.assertEqual(num_balances_added2, 0, "Duplicate balances were added when they shouldn't be")

        # Check that we can assign balances to a different account
        num_balances_added3 = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB,
                                    accnt = "bals_test_accnt", 
                                    path_to_balances = self.input_path
                                    )
        self.assertEqual(num_balances_added3, balances_to_add.shape[0], "Could not add balances to a different account")
    
    def test_load_balances_from_CLI(self):
        # Mostly a does-it-run test for integration (since components are unit tested)
        accnt = "new_cc"
        fintrackr.load_balances.load_balances_from_CLI(
            accnt_name = accnt, 
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_balances.csv"), 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_name = self.params["test_db_name"])
        
        bals_test_query = "SELECT date, amount FROM balances WHERE date=%s AND accnt_id=%s;"
        test_date = date(year=2025, month=10, day=2)
        accnt_id = self.FinDB.execute_query("SELECT id FROM data_sources WHERE name=%s", (accnt,))

        result = self.FinDB.execute_query(bals_test_query, (test_date,accnt_id[0][0]))
        self.assertEqual(len(result),1)