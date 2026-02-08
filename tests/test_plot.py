import unittest
import subprocess

from datetime import date

import fintrackr.testing_utils as utils
import fintrackr.plot

class TestEDLConverter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.params = utils.config_params()

        cls.FinDB = utils.set_up_test_DB(params=cls.params)

        # Some test fixtures shared by multiple tests:
        cls.path_to_test_transactions = utils.TEST_TRANSACTIONS_PATH

        # Add testing data to db - load transactions, add balances
        cls.accnt_name = "cc"
        cls.balance_date = date(year=2025, month=8, day=25)
        cls.balance_amount = 5000.00
        
        cls.FinDB.add_balance(
            accnt=cls.accnt_name,
            bal_date=cls.balance_date,
            bal_amt=cls.balance_amount
        )

        cls.FinDB.add_transactions(
            path_to_source_file = cls.path_to_test_transactions, 
            source_info = cls.accnt_name
        )
    
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

    def test_data_from_date_range(self):
        amts = fintrackr.plot.data_from_date_range(
            data_source = self.accnt_name, 
            date_range = ['8/1/2025','9/1/2025'], 
            username = self.params["user"], 
            pw = self.params["user_pw"], 
            db_name = self.params["test_db_name"]
        )

        bal_money = "$"+f"{self.balance_amount}"[0]+","+f"{self.balance_amount}"[1:]+"0"
        self.assertEqual(amts["balances"][0][1], bal_money, "data_from_date_range did not return correct balance amount")

        self.assertEqual(len(amts["transactions"]), 6, "data_from_date_range did not return the correct number of transactions") # assumes BETWEEN is inclusive