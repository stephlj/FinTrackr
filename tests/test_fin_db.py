# Tests fin_db.py (the DAL)
#
# The DAL is simple enough that most of these tests are probably unnecessary.
# but they're helpful as I'm still learning!
#
# Copyright (c) 2025, 2026 Stephanie Johnson

import unittest
import os
import pandas as pd

from datetime import date
from psycopg import errors as psql_errors
from decimal import Decimal

import fintrackr.testing_utils as utils
from fintrackr.dataclasses import Col_Def

class TestFinDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db; implicit test of init_db and add_user.
        cls.params = utils.config_params()
        cls.FinDB = utils.set_up_test_DB(params=cls.params)

    @classmethod
    def tearDownClass(cls):
        utils.tear_down_test_DB(db_conn=cls.FinDB, params=cls.params)
    
    def test_csv_to_staging(self):
        self.addCleanup(self.FinDB.execute_action, "DROP TABLE staging;")

        # This function adds rows to a staging table that should be empty at start

        path_to_test_transactions = os.path.join(utils.TEST_DATA_PATH, "test_data_cc.csv")
        transactions_to_add = pd.read_csv(path_to_test_transactions, header=None)
        element_to_match = Decimal(str(transactions_to_add.iloc[0,1])).quantize(Decimal('0.01'))

        # Define expected cols of staging as a result of loading this file:
        test_cols = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="numeric"),
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
        self.addCleanup(self.FinDB.execute_action, "DROP TABLE staging;")

        # Not sure I need this test, but it confirms expected behavior for learning purposes
        
        # Create a staging table
        # Note this test will BREAK if I change the balances table schema;
        # I could load the relevant columns and types from a dataclass.
        # For test simplicity and readability, keeping as is:
        self.FinDB.execute_action("CREATE TABLE staging (date date, amount numeric(12,2));")
        # Newbie note! Because I don't have a RETURNING clause, use execute_action not execute_query
        self.FinDB.execute_action("INSERT INTO staging (date, amount) VALUES (%s,%s);", (date(year=2025, month=9, day=9), Decimal('5000.00')))
        accnt = "primary_checking"
        with self.assertRaises(psql_errors.NotNullViolation):
            self.FinDB.add_balances_from_staging(accnt_name=accnt)
        
        _ = self.FinDB.add_data_source(source_name = accnt)
        num_new_bals = self.FinDB.add_balances_from_staging(accnt_name=accnt)
        self.assertEqual(num_new_bals, 1)

        # Make sure I can't add duplicates
        with self.assertRaises(psql_errors.UniqueViolation):
            self.FinDB.add_balances_from_staging(accnt_name=accnt)

    def test_add_transactions_from_staging(self):
        self.addCleanup(self.FinDB.execute_action, "DROP TABLE staging;")
        
        # Create a staging table
        # Note this test will BREAK if I change the balances table schema
        self.FinDB.execute_action("CREATE TABLE staging (posted_date date, amount numeric(12,2), description text);")
        self.FinDB.execute_action("INSERT INTO staging (posted_date, amount, description) VALUES (%s,%s,%s);", (date(year=2025, month=9, day=9), Decimal('55.00'), 'Pet insurance'))
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

    def test_get_balances_in_date_range(self):
        # Add some data to test against (specific to this test)
        accnt_name = "test_accnt"
        accnt_id = self.FinDB.add_data_source(source_name=accnt_name)
        self.FinDB.execute_action(
            "INSERT INTO balances (accnt_id, date, amount) VALUES (%s,%s,%s);", 
            (accnt_id, date(year=1988, month=8, day=8), Decimal('8888.88'))
        )
        self.FinDB.execute_action(
            "INSERT INTO balances (accnt_id, date, amount) VALUES (%s,%s,%s);", 
            (accnt_id, date(year=1990, month=9, day=9), Decimal('9999.99'))
        )
        self.FinDB.execute_action(
            "INSERT INTO balances (accnt_id, date, amount) VALUES (%s,%s,%s);", 
            (accnt_id, date(year=1991, month=1, day=1), Decimal('11111.11'))
        )
        
        # Try all 3 entries,  inclusive
        balances = self.FinDB.get_balances_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1988,month=7,day=1),date(year=1992,month=1,day=1)]
        )
        self.assertEqual(len(balances), 3)
        # So far they've returned in chronological order but in case that's not the case:
        balances.sort(key=lambda b: b.date)
        self.assertEqual(balances[0].amount, Decimal('8888.88'), "get_balances_in_date_range did not return correct balance amount")
        
        # Test for inclusivity on one end
        balances2 = self.FinDB.get_balances_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1990,month=9,day=9),date(year=1992,month=1,day=1)]
        )
        balances2.sort(key=lambda b: b.date)
        self.assertEqual(len(balances2), 2)
        self.assertEqual(balances2[0].amount, Decimal('9999.99'), "get_balances_in_date_range did not return correct balance amount for inclusive bounds")

        # Try a range that gets none
        balances3 = self.FinDB.get_balances_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=2025,month=9,day=9),date(year=2026,month=1,day=1)]
        )
        self.assertEqual(len(balances3), 0)
        
        # Test dates get properly sorted
        balances4 = self.FinDB.get_balances_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1990,month=10,day=1),date(year=1988,month=1,day=1)]
        )
        balances4.sort(key=lambda b: b.date)
        self.assertEqual(len(balances4), 2)
        self.assertEqual(balances4[0].amount, Decimal('8888.88'), "get_balances_in_date_range did not return correct balance amount for unsorted date range")

        # Test non-date type fails
        with self.assertRaises(TypeError):
            balances5 = self.FinDB.get_balances_in_date_range(
                accnt_name = accnt_name,
                date_range = ["9/9/1997", "1/1/1993"]
            )

    def test_get_transactions_in_date_range(self):
        # Add some data to test against (specific to this test)
        # Transactions are a little more complicated than balances
        accnt_name = "test_accnt2"
        accnt_id = self.FinDB.add_data_source(source_name=accnt_name)

        metadatum_id = self.FinDB.execute_scalar(
            "INSERT INTO data_load_metadata (date_added, username, source, data_source_id) VALUES (%s,%s,%s,%s) RETURNING id;",
            (
                date(year=2026, month=1, day=1),
                self.params["user"],
                "transactions_file.csv",
                accnt_id
             )
        )

        self.FinDB.execute_action(
            "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
            (date(year=1978, month=8, day=8), Decimal('-50.00'), 'Safeway', metadatum_id))
        self.FinDB.execute_action(
            "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
            (date(year=1978, month=8, day=8), Decimal('-400.00'), 'Rent', metadatum_id))
        self.FinDB.execute_action(
            "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
            (date(year=1979, month=9, day=9), Decimal('-55.00'), 'Safeway', metadatum_id))
        
        # Try all 3 entries,  inclusive
        trans = self.FinDB.get_transactions_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1977,month=7,day=1),date(year=1980,month=1,day=1)]
        )
        self.assertEqual(len(trans), 3)
        trans.sort(key=lambda t: t.date)
        self.assertEqual(trans[-1].amount, Decimal('-55.00'), "get_transactions_in_date_range did not return correct transaction amount")
        
        # Test for inclusivity on one end
        trans2 = self.FinDB.get_transactions_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1978,month=8,day=8),date(year=1980,month=1,day=1)]
        )
        self.assertEqual(len(trans2), 3)
        trans2.sort(key=lambda t: t.date)
        self.assertEqual(trans2[-1].amount, Decimal('-55.00'), "get_transactions_in_date_range did not return correct amount for inclusive bounds")

        # Try a range that gets none
        trans3 = self.FinDB.get_transactions_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=2025,month=9,day=9),date(year=2026,month=1,day=1)]
        )
        self.assertEqual(len(trans3), 0)
        
        # Test dates get properly sorted
        trans4 = self.FinDB.get_transactions_in_date_range(
            accnt_name = accnt_name, 
            date_range = [date(year=1980,month=10,day=1),date(year=1977,month=1,day=1)]
        )
        self.assertEqual(len(trans4), 3)
        trans4.sort(key=lambda t: t.date)
        self.assertEqual(trans4[-1].amount, Decimal('-55.00'), "get_transactions_in_date_range did not return correct amount for unsorted date range")

        # Test non-date type fails
        with self.assertRaises(TypeError):
            trans5 = self.FinDB.get_transactions_in_date_range(
                accnt_name = accnt_name,
                date_range = ["9/9/1997", "1/1/1993"]
            )
        