"""
Opens a connetion to the db and loads balances or transactions from csvs.

Copyright (c) 2026 Stephanie Johnson
"""

import yaml
import logging

from functools import wraps
from psycopg import errors as psql_errors
from typing import List

from dbcommons.dataclass_utils import csv_to_dataclass

from fintrackr.fin_db import FinDB
from fintrackr.utils import CONFIG_PATH, reformat_csv
from fintrackr.fin_dataclasses import Balance, Transaction, BAL_COL_DEFS, TRANS_COL_DEFS

class DataLoader:
    def __init__(self, user: str, pw: str, db_config: str=""):
        if db_config=='':
            self.db_config = CONFIG_PATH
        else:
            self.db_config=db_config

        with open(self.db_config, "r") as config_file:
            config = yaml.safe_load(config_file)
            self.db_name = config["db"]["db_name"]

        self.conn = FinDB(user=user, pw=pw, db_name=self.db_name)

        self._logger = logging.getLogger(__name__)

    def close(self):
        if getattr(self, "conn", None) is None:
            return
        try:
            self.conn.close()
        except Exception:
            self._logger.exception("DataLoader failed to close db connection cleanly")
        finally:
            self.conn = None

    def __del__(self):
        # Fall back safety net to make sure connection is closed when garbage collected
        self.close()

    def __enter__(self):
        # Use DataLoader within a "with" clause
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    def clean_up_staging(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            finally:
                self.conn.drop_staging()
        return wrapper
    
    @clean_up_staging
    def add_balances(self, accnt: str, bals_list: List[Balance]) -> int:
        """
        Load a list of Balance dataclasses into db.
        Will not allow duplicates to be added.

        Parameters
        ----------
        accnt: str
            Account name to log balances for (name in data_sources)
        bals_list: List[Balance]
            List of Balance dataclasses
        
        Return
        ------
        int
            Number of balances added. Zero if all balances to add were already in db.
        """        

        self.conn.create_staging(col_defs=BAL_COL_DEFS)
        num_staged_balances = self.conn.class_to_staging(insert_obj_list=bals_list)

        if num_staged_balances == 0:
            msg = f"No balances were staged; no balances will be added to db"
            self._logger.error(msg)
            raise ValueError(msg)
        
        try:
            num_new_balances = self.conn.add_balances_from_staging(accnt_name = accnt)
        except psql_errors.UniqueViolation as e:
            self._logger.error(f"Insertion into balances table under account {accnt} failed; all balances are already in the db (exception: {e})")
            raise
        except psql_errors.NotNullViolation as e:
            self._logger.error(f"Insertion into balances table failed with exception {e}; check account name {accnt} exists in db")
            raise
        except Exception as e:
            self._logger.exception(f"Insertion into balances table failed with exception: {e}")
            raise
        
        return num_new_balances

    @clean_up_staging
    def add_transactions(self, source_info: str, trans_list: List[Transaction], path_to_source_file: str) -> int:
        """
        Load a list of Transactions into the db and log the addition of these transactions
        in the data_load_metadata table.

        Only new transactions are added; duplicates (which have identity across the 3
        input columns of `posted_date`, `amount`, and `description` with an existing transaction row)
        are ignored.

        Parameters
        ----------
        source_info: str
            name of an account in data_sources
        trans_list: List[Transactions]
            One per row loaded from a csv
        path_to_source_file: str
            Path to a csv where every row is a transaction.
            This is to record the original source file from which the List[Transaction] was derived.

        Returns
        -------
        int
            Number of transactions added.
        """

        self.conn.create_staging(col_defs=TRANS_COL_DEFS)
        num_staged_transactions = self.conn.class_to_staging(insert_obj_list=trans_list)

        if num_staged_transactions == 0:
            msg = f"No transactions loaded from source file {path_to_source_file} to staging table; no transactions will be added"
            self._logger.error(msg)
            raise ValueError(msg)

        if num_staged_transactions != len(trans_list):
            msg = f"{num_staged_transactions} transactions were loaded into staging, but {len(trans_list)} were passed; something went wrong!"
            self._logger.error(msg)
            raise ValueError(msg)

        # We silently skip duplicates. Check how many there are first.
        num_not_dups = self.conn.check_dup_transactions()
            
        try:
            num_new_transactions = self.conn.add_transactions_from_staging(path_to_source_file=path_to_source_file, source_info=source_info)
        except psql_errors.NotNullViolation as e:
            self._logger.error(f"Insertion into transactions table failed with null violation (exception: {e}); check account name {source_info} exists in db")
            raise
        except Exception as e:
            self._logger.exception(f"Insertion into transactions table failed with exception: {e}")
            raise
        
        if num_new_transactions != num_staged_transactions:
            if num_not_dups != num_new_transactions:
                msg = "Not all staged transactions were loaded, but not because of duplicates; something went wrong!"
                self._logger.error(msg)
                raise ValueError(msg)
            num_dups = num_staged_transactions-num_not_dups
            self._logger.info(f"{num_dups} staged transactions are already in transactions table; {num_not_dups} were added")
                
        return num_new_transactions

    def add_balances_from_csv(self, path_to_csv: str, account_name: str)->int:
        # Load balances from csv into a list of Balance dataclasses, one dataclass per csv row; 
        # also handles input checking and formatting.

        bals = csv_to_dataclass(path_to_csv=path_to_csv, cls=Balance)

        if len(bals) == 0:
            msg = f"No balances successfully extracted from source file {path_to_csv}; no balances will be added to db"
            self._logger.error(msg)
            raise ValueError(msg)

        self._logger.info(f"Successfully logged data from file {path_to_csv} under account {account_name}")

        return self.add_balances(accnt=account_name, bals_list=bals)

    def add_transactions_from_csv(self, path_to_csv: str, account_name: str, config_path: str=CONFIG_PATH)->int:
        # Load transactions from csv into a list of Transaction dataclasses, one dataclass per csv row; 
        # also handles input checking and formatting.

        # Since we don't control the transaction csv format, try to wrangle what we got into what we need:
        reformtted_csv_path = reformat_csv(path_to_csv=path_to_csv, config_path=config_path)

        transactions = csv_to_dataclass(path_to_csv=reformtted_csv_path, cls=Transaction)

        if len(transactions) == 0:
            msg = f"No transactions successfully extracted from source file {path_to_csv}; no transactions will be added to db"
            self._logger.error(msg)
            raise ValueError(msg)

        self._logger.info(f"Successfully logged data from file {path_to_csv} under account {account_name}")

        return self.add_transactions(source_info=account_name, trans_list = transactions, path_to_source_file=path_to_csv)