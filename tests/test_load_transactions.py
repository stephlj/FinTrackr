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

        try:
            os.remove(os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv"))
        except:
            pass

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
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols.csv"), 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_config = utils.TEST_CONFIG_PATH)
        
        test_query = """
            SELECT t.posted_date, t.amount, t.description
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date=%s
            AND s.name=%s;
        """
        test_date = date(year=2024, month=7, day=23)
        
        result = self.FinDB.execute_query(test_query, (test_date,accnt))
        self.assertEqual(len(result),1)
        os.remove(os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv"))