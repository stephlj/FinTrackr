# test_db_integrations.py
#
# Tests functionality from both fin_db.py and load_data.py that require db connections.
#
# Copyright (c) 2025, 2026 Stephanie Johnson

import unittest
import os
import pandas as pd

from datetime import date
from psycopg import errors as psql_errors

import fintrackr.testing_utils as utils
from fintrackr.dataclasses import Col_Def
from fintrackr.load_data import add_balances, add_transactions, load_data_from_CLI

class TestDBIntegrations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db; implicit test of init_db and add_user.
        cls.params = utils.config_params()
        cls.FinDB = utils.set_up_test_DB(params=cls.params)

    @classmethod
    def tearDownClass(cls):
        utils.tear_down_test_DB(db_conn=cls.FinDB, params=cls.params)
    
    def test_load_data_add_balances(self):        
        # Use properly formatted csvs
        path_to_test_bals = os.path.join(utils.TEST_DATA_PATH,"test_balances_noheader.csv")
        balances_to_add = pd.read_csv(path_to_test_bals, header=None)
        name = "test_add_bals_integration"

        with self.assertRaises(psql_errors.NotNullViolation):
            _ = add_balances(db_conn = self.FinDB, 
                            accnt = name, 
                            path_to_balances = path_to_test_bals
                            )
        
        _ = self.FinDB.add_data_source(source_name = name)
        num_balances_added = add_balances(
                                    db_conn = self.FinDB, 
                                    accnt = name, 
                                    path_to_balances = path_to_test_bals
                                    )
        self.assertEqual(num_balances_added, balances_to_add.shape[0], "Number of added balances does not match file")
        
        # Check we can't add the same balances again:
        num_balances_added2 = add_balances(
                                    db_conn = self.FinDB,
                                    accnt = name, 
                                    path_to_balances = path_to_test_bals
                                    )
        self.assertEqual(num_balances_added2, 0, "Duplicate balances were added when they shouldn't be")

        # Check that we can assign balances to a different account
        new_name = "test_add_bals_integration2"
        _ = self.FinDB.add_data_source(source_name = new_name)
        num_balances_added3 = add_balances(
                                    db_conn = self.FinDB,
                                    accnt = new_name, 
                                    path_to_balances = path_to_test_bals
                                    )
        self.assertEqual(num_balances_added3, balances_to_add.shape[0], "Could not add duplicate balances to a different account")
    
    def test_load_data_add_transactions(self):
        # Use properly formatted csvs
        path_to_test_transactions = os.path.join(utils.TEST_DATA_PATH, "test_data_cc.csv")
        source_name = "cc"
        transactions_to_add = pd.read_csv(path_to_test_transactions, header=None)
        element_to_match = str(transactions_to_add.iloc[0,1])
        element_to_match = element_to_match[0] + "$" + element_to_match[1:] + "0"
        
        with self.assertRaises(psql_errors.NotNullViolation):
            num_transactions_added = add_transactions(
                db_conn = self.FinDB,
                path_to_source_file = path_to_test_transactions, 
                source_info = source_name
                )
        
        _ = self.FinDB.add_data_source(source_name = source_name)
        num_transactions_added = add_transactions(
            db_conn = self.FinDB,
            path_to_source_file = path_to_test_transactions, 
            source_info = source_name
            )
        self.assertEqual(num_transactions_added, transactions_to_add.shape[0], "Number of added transactions does not match file")
        self.assertEqual(element_to_match, 
                         self.FinDB.execute_query("SELECT amount FROM transactions WHERE description=%s;",('Concert tickets',))[0][0], 
                         "Data were scrambled when loaded into transactions"
                         )
        
        # Test that trying to upload the same file again fails
        num_transactions_added = add_transactions(
            db_conn = self.FinDB,
            path_to_source_file = path_to_test_transactions, 
            source_info = source_name
            )
        self.assertEqual(num_transactions_added, 0, "Duplicates should not have been successfully loaded")

        # Test what happens when partial duplicates are added
        # This file is nearly the same, with 2 different lines
        additional_transactions_path = os.path.join(utils.TEST_DATA_PATH,"test_csv_wrongtype_fixed.csv")
        num_transactions_added = add_transactions(
            db_conn = self.FinDB,
            path_to_source_file = additional_transactions_path, 
            source_info = source_name
            )
        self.assertEqual(num_transactions_added, 2, "Only two non-duplicate transactions should have been loaded")

    def test_load_data_from_CLI(self):
        self.addCleanup(os.remove, os.path.join(utils.TEST_DATA_PATH, "test_balances_REFORMAT.csv"))
        self.addCleanup(os.remove, os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv"))
        
        # Mostly a does-it-run test for integration (since components are unit tested)
        # Try adding balances
        bal_accnt = "new_checking"
        load_data_from_CLI(
            accnt_name = bal_accnt, 
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_balances.csv"), #Since this IS an integration test, use an input file that needs reformatting
            username = self.params["user"], 
            pw = self.params["user_pw"],
            trans=False,
            add_as_new_acct=True,
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

        # Try adding transactions
        trans_accnt = "new_cc"
        load_data_from_CLI(
            accnt_name = trans_accnt, 
            filepath=os.path.join(utils.TEST_DATA_PATH, "test_csv_header_wrongcols.csv"), 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            trans=True,
            add_as_new_acct=True,
            db_config = utils.TEST_CONFIG_PATH)
        
        trans_test_query = """
            SELECT t.posted_date, t.amount, t.description
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date=%s
            AND s.name=%s;
        """
        trans_test_date = date(year=2023, month=7, day=23)
        
        trans_result = self.FinDB.execute_query(trans_test_query, (trans_test_date, trans_accnt))
        self.assertEqual(len(trans_result),1)
    
    