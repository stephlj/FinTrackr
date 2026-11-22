# test_db_integrations.py
#
# Integration tests for functions in load_data.py and plot_accnt_balances.py 
# that need a db to test against.
#
# Copyright (c) 2025, 2026 Stephanie Johnson

import unittest
import os, subprocess
import pandas as pd

from datetime import date
from decimal import Decimal
from psycopg import errors as psql_errors

from fintrackr.init_db import fin_init
from fintrackr.add_user import add_fin_user
from fintrackr.fin_dataclasses import Balance, Transaction
from fintrackr.fin_db import FinDB
from fintrackr.load_data import DataLoader
from fintrackr.plot_accnt_balances import plot_accnt_balances

from utils_for_tests import TEST_CONFIG_PATH, TEST_DATA_PATH, config_params_for_tests

class TestDBIntegrations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make a test db; note that these DO NOT test fin_init and add_fin_user.
        cls.params = config_params_for_tests(test_config_path=TEST_CONFIG_PATH)

        fin_init(admin_pw=cls.params["owner_pw"], path_to_config=cls.params["config_path"])
        add_fin_user(name=cls.params["user"], pw=cls.params["user_pw"], admin_pw=cls.params["owner_pw"], path_to_config=cls.params["config_path"])

        cls.dl = DataLoader(user=cls.params["user"], pw=cls.params["user_pw"], db_config=TEST_CONFIG_PATH)

    @classmethod
    def tearDownClass(cls):
        cls.dl.close()

        # Delete testing db
        exit_code = subprocess.run(["dropdb", cls.params["test_db_name"]])
        exit_code2 = subprocess.run(["dropuser",cls.params["user"]])
        exit_code3 = subprocess.run(["dropuser",cls.params["test_owner"]])

        # We put these at the end to ensure teardown completes even if one of these fails.
        assert exit_code.returncode==0, "Failed to remove testing db, must now remove manually"
        assert exit_code2.returncode==0, "Failed to remove testing user, must now remove manually"
        assert exit_code3.returncode==0, "Failed to remove testing db owner, must now remove manually"
    
    def test_load_data_add_balances(self):
        bals = [Balance(balance_date=date(year=2026,month=6,day=5), amount=Decimal('2001.20')), 
                Balance(balance_date=date(year=2025,month=10,day=10), amount=Decimal('4500.04'))]
        accnt_name="test_add_bals_from_cls"

        with self.assertRaises(psql_errors.NotNullViolation):
            _ = self.dl.add_balances(accnt=accnt_name,bals_list=bals)

        # Now add the account
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            dbconn.add_data_source(source_name=accnt_name)
        
        self.assertEqual(len(bals), self.dl.add_balances(accnt="test_add_bals_from_cls",bals_list=bals))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual(date(year=2026,month=6,day=5), 
                            dbconn.execute_scalar("SELECT balance_date FROM balances WHERE amount=%s;",(Decimal('2001.20'),)))
            accnt_id = dbconn.get_data_source_id(source_name=accnt_name)
            self.assertEqual(accnt_id,
                dbconn.execute_scalar("SELECT accnt_id FROM balances WHERE amount=%s AND balance_date=%s;",(Decimal('2001.20'),date(year=2026,month=6,day=5))))

        # Make sure we can't add the same balances again:
        with self.assertRaises(psql_errors.UniqueViolation):
            _ = self.dl.add_balances(accnt=accnt_name,bals_list=bals)

        # Check that we can add under a different account name
        new_accnt_name = "test_add_bals_from_cls_2"
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            dbconn.add_data_source(source_name=new_accnt_name)
        self.assertEqual(len(bals), self.dl.add_balances(accnt=new_accnt_name, bals_list=bals))

        # Check that we can add under a different account name - but not if the only difference is case
        # (this is an integration test)
        new_accnt_name_upper = "Test_add_bals_from_cls_2"
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            with self.assertRaises(psql_errors.UniqueViolation):
                dbconn.add_data_source(source_name=new_accnt_name_upper)
        
    def test_load_data_add_balances_from_csv(self):        
        path_to_csv = os.path.join(TEST_DATA_PATH,"test_balances.csv")
        accnt_name = "test_add_bals_from_csv"

        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = accnt_name)
        self.assertEqual(3, self.dl.add_balances_from_csv(path_to_csv=path_to_csv, account_name=accnt_name))

        # Check that we reject malformed input
        bad_accnt_name = "test_add_bals_from_bad_csv"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = bad_accnt_name)
        path_to_bad_csv = os.path.join(TEST_DATA_PATH, "test_balances_noheader.csv")
        with self.assertRaises(ValueError):
            _ = self.dl.add_balances_from_csv(path_to_csv=path_to_bad_csv, account_name=bad_accnt_name)

        # Check that we reject csvs with duplicate lines
        dups_accnt_name = "test_add_bals_dups"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = dups_accnt_name)
        path_to_dups_csv = os.path.join(TEST_DATA_PATH, "test_balances_dups.csv")
        with self.assertRaises(psql_errors.UniqueViolation):
            _ = self.dl.add_balances_from_csv(path_to_csv=path_to_dups_csv, account_name=dups_accnt_name)
        # make sure nothing got loaded
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            dups_id = db_conn.get_data_source_id(source_name=dups_accnt_name)
            self.assertEqual(0,len(db_conn.execute_query("SELECT balance_date FROM balances WHERE accnt_id=%s;",(dups_id,))))
                             
    def test_load_data_add_transactions(self):
        # add_transactions takes the path to the source csv for record-keeping, but here we'll load
        # a list of transactions directly
        trans = [Transaction(posted_date=date(year=2022,month=2,day=2), amount=Decimal('222.20'), description="trans0"), 
                        Transaction(posted_date=date(year=2022,month=11,day=11), amount=Decimal('1111.22'), description="trans1")]
        accnt_name="test_add_trans_from_cls"
        path_to_fake_csv = "fake_csv_path"

        with self.assertRaises(psql_errors.NotNullViolation):
            _ = self.dl.add_transactions(source_info=accnt_name, trans_list=trans, path_to_source_file=path_to_fake_csv)

        # Now add the account
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            dbconn.add_data_source(source_name=accnt_name)

        self.assertEqual(len(trans), self.dl.add_transactions(source_info=accnt_name, trans_list=trans, path_to_source_file=path_to_fake_csv))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual(date(year=2022,month=11,day=11), 
                            dbconn.execute_scalar("SELECT posted_date FROM transactions WHERE amount=%s;",(Decimal('1111.22'),)))
            q="""
                SELECT d.account_name 
                FROM data_sources AS d 
                INNER JOIN data_load_metadata AS m ON 
                    m.data_source_id=d.id 
                INNER JOIN transactions AS t ON 
                    t.metadatum_id=m.id 
                WHERE t.posted_date=%s;
            """
            self.assertEqual(accnt_name,
                dbconn.execute_scalar(q,(date(year=2022,month=2,day=2),)))

        # Make sure we can't add duplicates
        with self.assertRaises(psql_errors.UniqueViolation):
            _ = self.dl.add_transactions(source_info=accnt_name, trans_list=trans, path_to_source_file=path_to_fake_csv)

        # We don't allow duplicates, even under a different account name
        new_accnt_name = "test_add_trans_from_cls_2"
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            dbconn.add_data_source(source_name=new_accnt_name)
        with self.assertRaises(psql_errors.UniqueViolation):
            _ = self.dl.add_transactions(source_info=new_accnt_name, trans_list=trans, path_to_source_file=path_to_fake_csv)
        
        # Allow duplicates with a different sign on amount (e.g. debit from checking account to pay cc, matched by a positive transaction on cc)
        # But these must have a different source file name
        trans2 = [Transaction(posted_date=date(year=2022,month=2,day=2), amount=Decimal('222.20'), description="trans0"), 
                    Transaction(posted_date=date(year=2022,month=11,day=11), amount=Decimal('-1111.22'), description="trans1")]
        with self.assertRaises(psql_errors.UniqueViolation):
            _ = self.dl.add_transactions(source_info=new_accnt_name, trans_list=trans2, path_to_source_file=path_to_fake_csv)
        path_to_fake_csv2 = "fake_csv_path2"
        self.assertEqual(1, self.dl.add_transactions(source_info=new_accnt_name, trans_list=trans2, path_to_source_file=path_to_fake_csv2))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual(date(year=2022,month=11,day=11), 
                dbconn.execute_scalar("SELECT posted_date FROM transactions WHERE amount=%s;",(Decimal('-1111.22'),)))
            q="""
                SELECT d.account_name 
                FROM data_sources AS d 
                INNER JOIN data_load_metadata AS m ON 
                    m.data_source_id=d.id 
                INNER JOIN transactions AS t ON 
                    t.metadatum_id=m.id 
                WHERE t.amount=%s;
            """
            self.assertEqual(new_accnt_name,
                dbconn.execute_scalar(q,((Decimal('-1111.22'),))))

    
    def test_load_data_add_transactions_from_csv(self):
        # Start with a simple case
        # Note we DON'T use the "_fixed.csv" versions because that's the output of reformat_csv - 
        # but not an acceptable input (won't match config!)
        path_to_csv = os.path.join(TEST_DATA_PATH,"test_csv_simple_header.csv")
        csv_out = os.path.join(TEST_DATA_PATH,"test_csv_simple_header_REFORMAT.csv")
        self.addCleanup(os.remove, csv_out)
        accnt_name = "test_add_trans_from_csv"

        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = accnt_name)
        self.assertEqual(10, self.dl.add_transactions_from_csv(path_to_csv=path_to_csv, account_name=accnt_name, config_path=TEST_CONFIG_PATH))
        
        # Check that various acceptable formats work. This is the primary integration test with reformat_csv
        # Extra columns and also weird characters in description:
        path_to_csv = os.path.join(TEST_DATA_PATH,"test_csv_header_extracols.csv")
        csv_out = os.path.join(TEST_DATA_PATH,"test_csv_header_extracols_REFORMAT.csv")
        self.addCleanup(os.remove, csv_out)
        accnt_name = "test_add_trans_from_csv2"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = accnt_name)
        self.assertEqual(10, self.dl.add_transactions_from_csv(path_to_csv=path_to_csv, account_name=accnt_name, config_path=TEST_CONFIG_PATH))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual("Alaska airlines REF # 123-456", 
                dbconn.execute_scalar("SELECT description FROM transactions WHERE amount=%s;",(Decimal('-536.59'),)))
            self.assertEqual(date(year=2024,month=9,day=9), 
                dbconn.execute_scalar("SELECT posted_date FROM transactions WHERE description=%s;",('Concert* tickets',)))

        # No header, match on column type
        path_to_csv = os.path.join(TEST_DATA_PATH,"test_csv_noheader2.csv")
        csv_out = os.path.join(TEST_DATA_PATH,"test_csv_noheader2_REFORMAT.csv")
        self.addCleanup(os.remove, csv_out)
        accnt_name = "test_add_trans_from_csv3"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = accnt_name)
        self.assertEqual(10, self.dl.add_transactions_from_csv(path_to_csv=path_to_csv, account_name=accnt_name, config_path=TEST_CONFIG_PATH))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual(date(year=2025,month=8,day=29), 
                dbconn.execute_scalar("SELECT posted_date FROM transactions WHERE description=%s;",('WaterCo*',)))

        # No header, match on column type, start with two check rows
        path_to_csv = os.path.join(TEST_DATA_PATH,"test_csv_noheader3.csv")
        csv_out = os.path.join(TEST_DATA_PATH,"test_csv_noheader3_REFORMAT.csv")
        self.addCleanup(os.remove, csv_out)
        accnt_name = "test_add_trans_from_csv4"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = accnt_name)
        self.assertEqual(10, self.dl.add_transactions_from_csv(path_to_csv=path_to_csv, account_name=accnt_name, config_path=TEST_CONFIG_PATH))
        with FinDB(user=self.params["user"],pw=self.params["user_pw"],db_name=self.params["test_db_name"]) as dbconn:
            self.assertEqual(Decimal('-43.82'), # not the check number
                dbconn.execute_scalar("SELECT amount FROM transactions WHERE posted_date=%s;",(date(year=1991,month=1,day=1),)))
        
        # Check that we reject malformed input 
        bad_accnt_name = "test_add_trans_from_bad_csv"
        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            _ = db_conn.add_data_source(source_name = bad_accnt_name)
        path_to_bad_csv = os.path.join(TEST_DATA_PATH, "test_csv_wrongheader.csv")
        with self.assertRaises(ValueError):
            _ = self.dl.add_transactions_from_csv(path_to_csv=path_to_bad_csv, account_name=bad_accnt_name, config_path=TEST_CONFIG_PATH)

    def test_plot_accnt_balances(self):
        # Add some data for this test, to keep it independent
        accnt = "plot_me"

        with FinDB(user=self.params["user"], pw=self.params["user_pw"], db_name=self.params["test_db_name"]) as db_conn:
            accnt_id = db_conn.add_data_source(source_name=accnt)
            # add a balance as a reference point
            db_conn.execute_action(
                "INSERT INTO balances (accnt_id, balance_date, amount) VALUES (%s,%s,%s);", 
                (accnt_id, date(year=2008, month=8, day=8), Decimal('8888.88'))
            ) 
            # add a couple transactions
            metadatum_id = db_conn.execute_scalar(
                "INSERT INTO data_load_metadata (date_added, username, source, data_source_id) VALUES (%s,%s,%s,%s) RETURNING id;",
                (
                    date(year=2008, month=11, day=1),
                    self.params["user"],
                    "transactions_file.csv",
                    accnt_id
                )
            )
            db_conn.execute_action(
                "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
                (date(year=2008, month=8, day=8), Decimal('-50.00'), 'Safeway', metadatum_id))
            db_conn.execute_action(
                "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
                (date(year=2008, month=8, day=9), Decimal('-400.00'), 'Rent', metadatum_id))
            db_conn.execute_action(
                "INSERT INTO transactions (posted_date, amount, description, metadatum_id) VALUES (%s,%s,%s,%s);", 
                (date(year=2008, month=9, day=9), Decimal('-55.00'), 'Safeway', metadatum_id))
        # A does-it-run test:
        plot_accnt_balances(
            accnt_name = accnt, 
            date_range = [date(year=2008, month=7, day=1), date(year=2008, month=11, day=1)], 
            username = self.params["user"], 
            pw = self.params["user_pw"],
            db_config = TEST_CONFIG_PATH)
    
    