# test_db_integrations.py
#
# Tests functionality from both fin_db.py and load_data.py that require db connections.
#
# Copyright (c) 2025, 2026 Stephanie Johnson

import unittest
import subprocess, os
import pandas as pd

from datetime import date
from psycopg import errors as psql_errors

import fintrackr.testing_utils as utils
from fintrackr.utils import Col_Def
from fintrackr.load_data import add_balances, add_transactions

class TestDBIntegrations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db, in the process also tests init_db and add_user.
        
        cls.params = utils.config_params()

        cls.FinDB = utils.set_up_test_DB(params=cls.params)

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
    
    def test_csv_to_staging(self):
        # This function adds rows to a staging table that should be empty at start

        path_to_test_transactions = os.path.join(utils.TEST_DATA_PATH, "test_data_cc.csv")
        transactions_to_add = pd.read_csv(path_to_test_transactions, header=None)
        element_to_match = str(transactions_to_add.iloc[0,1])
        element_to_match = element_to_match[0] + "$" + element_to_match[1:] + "0"

        # Define expected cols of staging as a result of loading this file:
        test_cols = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]
                     
        num_rows_added = self.FinDB.csv_to_staging(csv_path=path_to_test_transactions, csv_columns = test_cols)
        self.assertEqual(num_rows_added, transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(element_to_match, 
                         self.FinDB.execute_query("SELECT amount FROM staging WHERE description=%s;", ('Concert tickets',))[0][0], 
                         "Data were scrambled when copied into staging"
                         )
        
        # test that staging has NOT been cleared at this point
        self.assertEqual(len(self.FinDB.execute_query("SELECT posted_date, amount, description FROM staging;")), transactions_to_add.shape[0], "Staging table didn't persist")

        # test that it does clear if we try to add new transactions
        num_rows_added = self.FinDB.csv_to_staging(csv_path=path_to_test_transactions, csv_columns = test_cols)
        self.assertEqual(num_rows_added, transactions_to_add.shape[0], "Rows added to staging table does not match file")
        self.assertEqual(len(self.FinDB.execute_query("SELECT posted_date, amount, description FROM staging;")), transactions_to_add.shape[0], "Staging table wasn't cleared")

    def test_add_balances_from_staging(self):
        # Not sure I need this test, but it confirms expected behavior for learning purposes
        
        # Create a staging table
        # Note this test will BREAK if I change the balances table schema;
        # I could load the relevant columns and types from a dataclass.
        # For test simplicity and readability, keeping as is:
        self.FinDB.execute_action("CREATE TABLE staging (date date, amount money);")
        # Newbie note! Because I don't have a RETURNING clause, use execute_action not execute_query
        self.FinDB.execute_action("INSERT INTO staging (date, amount) VALUES (%s,%s);", (date(year=2025, month=9, day=9), '5000.00'))
        accnt = "primary_checking"
        with self.assertRaises(psql_errors.NotNullViolation):
            self.FinDB.add_balances_from_staging(accnt_name=accnt)
        
        _ = self.FinDB.add_data_source(source_name = accnt)
        num_new_bals = self.FinDB.add_balances_from_staging(accnt_name=accnt)
        self.assertEqual(num_new_bals, 1)

        # Make sure I can't add duplicates
        with self.assertRaises(psql_errors.UniqueViolation):
            self.FinDB.add_balances_from_staging(accnt_name=accnt)
        
        # Clean up
        self.FinDB.execute_action("DROP TABLE staging;")

    def test_add_transactions_from_staging(self):
        # Create a staging table
        # Note this test will BREAK if I change the balances table schema
        self.FinDB.execute_action("CREATE TABLE staging (posted_date date, amount money, description text);")
        self.FinDB.execute_action("INSERT INTO staging (posted_date, amount, description) VALUES (%s,%s,%s);", (date(year=2025, month=9, day=9), '55.00', 'Concert tickets'))
        accnt = "primary_cc"
        filepath = "trans_from_staging_test.csv"

        with self.assertRaises(psql_errors.NotNullViolation):
            self.FinDB.add_transactions_from_staging(path_to_source_file = filepath, source_info=accnt)
        
        _ = self.FinDB.add_data_source(source_name = accnt)
        num_new_bals = self.FinDB.add_transactions_from_staging(path_to_source_file = filepath, source_info=accnt)
        self.assertEqual(num_new_bals, 1)

        # Make sure I can't load this exact same file again
        with self.assertRaises(psql_errors.UniqueViolation):
            self.FinDB.add_transactions_from_staging(path_to_source_file = filepath, source_info=accnt)

        # Make sure I can't load same transactions under a different filename
        filepath2 = "new_trans.csv"
        num_dup_trans = self.FinDB.add_transactions_from_staging(path_to_source_file = filepath2, source_info=accnt)
        self.assertEqual(num_dup_trans, 0, "Duplicates should not have been added to transactions table")

        self.FinDB.execute_action("DROP TABLE staging;")
    
    # def test_data_from_date_range(self):
    #     # pytest runs each test case independently, so re-set-up the db
    #     # Neither of these functions allow duplicates
    #     # Not ideal that this unittest depends on functions from another module ... 
    #     add_balances(
    #         FinDB = self.FinDB,
    #         accnt=self.source_info,
    #         bal_date=self.balance_date,
    #         bal_amt=self.balance_amount
    #     )
    #     add_transactions(
    #         FinDB = self.FinDB,
    #         path_to_source_file = self.path_to_test_transactions, 
    #         source_info = self.source_info
    #     )

    #     amts = self.FinDB.data_from_date_range(
    #         data_source = self.source_info, 
    #         date_range = [date(year=2025,month=9,day=5),date(year=2025,month=9,day=10)]
    #     )
        
    #     bal_money = "$"+f"{self.balance_amount}"[0]+","+f"{self.balance_amount}"[1:]+"0"
    #     self.assertEqual(amts["balances"][0].amount, bal_money, "data_from_date_range did not return correct balance amount")

    #     self.assertEqual(len(amts["transactions"]), 2, "data_from_date_range did not return the correct number of transactions") # assumes BETWEEN is inclusive


