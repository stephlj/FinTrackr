# test_load_data.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import subprocess, os
import pandas as pd

from datetime import date

import fintrackr.load_data
import fintrackr.testing_utils as utils

class TestLoadData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = utils.config_params()
        cls.FinDB = utils.set_up_test_DB(params=cls.params)

        # Shared by multiple tests
        cls.source_info = "cc"
        cls.balance_date = date(year=2025, month=9, day=9)
        cls.balance_amount = 5000.00
        
        cls.path_to_test_bals = os.path.join(utils.TEST_DATA_PATH,"test_balances.csv")
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
        
        balances_to_add = pd.read_csv(self.path_to_test_bals, header=None)

        num_balances_added = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB, 
                                    accnt = self.source_info, 
                                    path_to_balances = self.path_to_test_bals
                                    )
        self.assertEqual(num_balances_added, balances_to_add.shape[0], "Number of added balances does not match file")
        
        # Check we can't add the same balances again:
        num_balances_added2 = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB,
                                    accnt = self.source_info, 
                                    path_to_balances = self.path_to_test_bals
                                    )
        self.assertEqual(num_balances_added2, 0, "Duplicate balances were added when they shouldn't be")

        # Check that we can assign balances to a different account
        num_balances_added3 = fintrackr.load_balances.add_balances_from_csv(
                                    FinDB = self.FinDB,
                                    accnt = "bals_test_accnt", 
                                    path_to_balances = self.path_to_test_bals
                                    )
        self.assertEqual(num_balances_added3, balances_to_add.shape[0], "Could not add balances to a different account")
    
    def test_add_transactions(self):
        # Add_transactions calls csv_to_staging (which we test separately above)

        num_transactions_added = fintrackr.load_data.add_transactions(
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
        num_transactions_added = fintrackr.load_data.add_transactions(
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

        num_transactions_added = fintrackr.load_data.add_transactions(
            FinDB = self.FinDB,
            path_to_source_file = additional_transactions_path, 
            source_info = self.source_info
            )
        self.assertEqual(num_transactions_added, num_new_trans, "Duplicates should not have been successfully loaded")
    
    def test_load_data_from_CLI(self):
        # Mostly a does-it-run test for integration (since components are unit tested)
        # Try adding balances
        bal_accnt = "new_checking"
        fintrackr.load_balances.load_balances_from_CLI(
            accnt_name = bal_accnt, 
            filepath=self.path_to_test_bals, #same file as in other tests, but adding under a different accnt
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_config = utils.TEST_CONFIG_PATH)
        
        bal_test_query = """
            SELECT b.date, b.amount
            FROM balances AS b
            JOIN data_sources AS s ON s.id = b.accnt_id
            WHERE b.date=%s
            AND s.name=%s;
        """
        bal_test_date = date(year=2025, month=10, day=2)

        bal_result = self.FinDB.execute_query(bal_test_query, (bal_test_date, bal_accnt))
        self.assertEqual(len(bal_result),1)

        trans_accnt = "new_cc"
        fintrackr.load_data.load_data_from_CLI(
            accnt_name = trans_accnt, 
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols.csv"), 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_config = utils.TEST_CONFIG_PATH)
        
        trans_test_query = """
            SELECT t.posted_date, t.amount, t.description
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date=%s
            AND s.name=%s;
        """
        trans_test_date = date(year=2024, month=7, day=23)
        
        trans_result = self.FinDB.execute_query(trans_test_query, (trans_test_date, trans_accnt))
        self.assertEqual(len(trans_result),1)
        os.remove(os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv"))