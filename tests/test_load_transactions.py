# test_load_transactions.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import subprocess, os
import pandas as pd

from datetime import date

import fintrackr.load_transactions
import fintrackr.testing_utils as utils

class TestLoadTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = utils.config_params()
        cls.FinDB = utils.set_up_test_DB(params=cls.params)

        # Shared by multiple tests
        cls.source_info = "cc"

        cls.path_to_test_transactions = os.path.join(utils.TEST_DATA_PATH, "test_data_cc.csv")
        cls.transactions_to_add = pd.read_csv(cls.path_to_test_transactions, header=None)
        cls.element_to_match = str(cls.transactions_to_add.iloc[1,1])
        cls.element_to_match = cls.element_to_match[0] + "$" + cls.element_to_match[1:] + "0"

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

    def test_add_transactions(self):
        # Add_transactions calls csv_to_staging (which we test separately above)

        num_transactions_added = fintrackr.load_transactions.add_transactions(
            FinDB = self.FinDB,
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
        num_transactions_added = fintrackr.load_transactions.add_transactions(
            FinDB = self.FinDB,
            path_to_source_file = self.path_to_test_transactions, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, 0, "Duplicates should not have been successfully loaded")

        # Test what happens when partial duplicates are added
        additional_transactions_path = os.path.join(utils.TEST_DATA_PATH,"test_data_checking.csv")
        addtl_trans = pd.read_csv(additional_transactions_path, header=None)
        num_new_trans = len(addtl_trans)
        dup_trans = self.transactions_to_add.loc[self.transactions_to_add.iloc[:,2]=="Safeway"]
        addtl_trans = pd.concat([addtl_trans, dup_trans])

        num_transactions_added = fintrackr.load_transactions.add_transactions(
            FinDB = self.FinDB,
            path_to_source_file = additional_transactions_path, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, num_new_trans, "Duplicates should not have been successfully loaded")
    
    def test_load_transctions_from_CLI(self):
        # Mostly a does-it-run test for integration (since components are unit tested)
        accnt = "new_cc"
        fintrackr.load_transactions.load_transctions_from_CLI(
            accnt_name = accnt, 
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrong_cols.csv"), 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_name = self.params["test_db_name"])
        
        test_query = "SELECT date, amount, description FROM transactions WHERE date=%s AND accnt_id=%s;"
        test_date = date(year=2025, month=7, day=23)
        accnt_id = self.FinDB.execute_query("SELECT id FROM data_sources WHERE name=%s", (accnt,))

        result = self.FinDB.execute_query(test_query, (test_date,accnt_id[0][0]))
        self.assertEqual(len(result),1)