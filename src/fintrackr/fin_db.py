# fin_db.py
#
# Copyright (c) 2025 Stephanie Johnson
"""
Class that connects to the database and manages interactions with it.

This is the database access layer; business logic should be elsewhere.

Copyright (c) 2025, 2026 Stephanie Johnson
"""

import psycopg
import logging
from typing import List

from datetime import date
from dbcommons.db_conn import DBConn

from fintrackr.fin_dataclasses import Transaction, Balance, BAL_COL_NAMES, TRANS_COL_NAMES

logger = logging.getLogger(__name__)

class FinDB(DBConn):
    def __init__(self, user: str, pw: str, db_name: str):
        # Use super() because I've now override base class init
        super().__init__(user=user, pw=pw, db_name=db_name)
        self.user = user
        self._logger = logging.getLogger(__name__)
    
    def get_all_data_sources(self) -> List[str]:
        # Returns a list of data_sources names
        names_list = self.execute_query("SELECT account_name FROM data_sources;")
        # unpack the list of dicts into a list
        return [n['account_name'] for n in names_list]
    
    def get_data_source_id(self, source_name: str) -> int:
        return self.execute_scalar("SELECT id FROM data_sources WHERE account_name=%s;", (source_name,))
    
    def add_data_source(self, source_name: str) -> int:
        # Returns id after insertion
        source_id_list = self.execute_query("INSERT INTO data_sources (account_name) VALUES (%s) RETURNING id;", (source_name,))
        return source_id_list[0]["id"]
    
    def add_balances_from_staging(self, accnt_name: str) -> int:
        # Insert balances that are in a staging table into the balances table of the db, under accnt_name.
        # Return number of inserted rows.
        # Will return an empty list if (date, amount) already exists (violation of that unique constraint)
        # and a NotNullViolation exception if accnt_name isn't already in data_sources
        
        balances_query = "INSERT INTO balances (balance_date, amount, accnt_id) " \
            "SELECT s.balance_date, s.amount, (select id from data_sources where account_name = %s) " \
            "FROM staging AS s " \
            "RETURNING *;"
        
        # For reference, another way of doing the same thing:
        # balances_query = "INSERT INTO balances (balance_date, amount, accnt_id) " \
        #     "SELECT s.balance_date, s.amount, d.id " \
        #     "FROM staging AS s " \
        #     "CROSS JOIN data_sources AS d WHERE account_name = %s "\
        #     "RETURNING *;"
        # However this just returns an empty list if account_name doesn't exist, rather than a NotNullViolation, so
        # preferring the first version (see commented out code below to raise the error I would want)

        rows_added = self.execute_query(balances_query, (accnt_name,))

        # if len(rows_added) == 0 and self.get_data_source_id is None:
        #     raise psycopg.errors.NotNullViolation(f"Account {accnt_name} does not exist; cannot add balances for that account")

        return len(rows_added)
    
    def add_transactions_from_staging(self, path_to_source_file: str, source_info: str) -> int:
        # Insert transactions that are in a staging table into the transactions table of the db.
        # Return number of inserted rows. Returns zero if all transactions in staging are already in db.

        # Log that these transactions were added today in the metadata table
        today_date = date.today()

        # Option 1:
        source_id= self.get_data_source_id(source_info)
        if source_id is None:
            raise psycopg.errors.NotNullViolation(f"Account {source_info} does not exist; cannot add transactions for that account")
        transactions_query = """
            WITH joined AS ( 
                SELECT s.* 
                FROM staging s 
                LEFT JOIN transactions t ON 
                    t.posted_date = s.posted_date AND 
                    t.amount = s.amount AND 
                    t.description = s.description  
                    WHERE t.id IS NULL 
                ), 
                meta AS ( 
                    INSERT INTO data_load_metadata 
                        (date_added, username, source, data_source_id)
                    VALUES (%s, %s, %s, %s) 
                    RETURNING id 
                ) 
            INSERT INTO transactions (posted_date, amount, description, metadatum_id) 
            SELECT posted_date, amount, description, meta.id 
            FROM joined, meta 
            RETURNING *;
            """
        rows_added = self.execute_query(transactions_query, (today_date, self.user, path_to_source_file, source_id))
    
        # Option 2: This returns an empty set if EITHER all transactions in staging are aleady in db,
        # OR account isn't in data_sources
        # transactions_query = """
        #     WITH joined AS ( 
        #         SELECT s.* 
        #         FROM staging s 
        #         LEFT JOIN transactions t ON 
        #             t.posted_date = s.posted_date AND 
        #             t.amount = s.amount AND 
        #             t.description = s.description  
        #             WHERE t.id IS NULL 
        #         ), 
        #         meta AS ( 
        #             INSERT INTO data_load_metadata 
        #                 (date_added, username, source, data_source_id)
        #             SELECT %s, %s, %s, id
        #             FROM data_sources WHERE name=%s 
        #             RETURNING id  
        #     ) 
        #     INSERT INTO transactions (posted_date, amount, description, metadatum_id) 
        #     SELECT posted_date, amount, description, meta.id 
        #     FROM joined, meta 
        #     RETURNING *;
        #     """
        # rows_added = self.execute_query(transactions_query, (today_date, self.user, path_to_source_file, source_info))

        # Option 3: This returns the NOTNULLVIOLATION I want if source_info doesn't exist in data_sources,
        # but is apparently pretty janky SQL ... 
        # transactions_query = """
        #     WITH joined AS ( 
        #         SELECT s.* 
        #         FROM staging s 
        #         LEFT JOIN transactions t ON 
        #             t.posted_date = s.posted_date AND 
        #             t.amount = s.amount AND 
        #             t.description = s.description  
        #             WHERE t.id IS NULL 
        #         ), 
        #         meta AS ( 
        #             INSERT INTO data_load_metadata 
        #                 (date_added, username, source, data_source_id)
        #             VALUES (%s, %s, %s, (SELECT id FROM data_sources WHERE name=%s)) 
        #             RETURNING id  
        #     ) 
        #     INSERT INTO transactions (posted_date, amount, description, metadatum_id) 
        #     SELECT posted_date, amount, description, meta.id 
        #     FROM joined, meta 
        #     RETURNING *;
        #     """
        # rows_added = self.execute_query(transactions_query, (today_date, self.user, path_to_source_file, source_info))

        if len(rows_added) == 0:
            # Check if nothing was added because everything in staging is already in db.
            # If not, raise error.
            check_dups = "SELECT s.* " \
                "    FROM staging s " \
                "    LEFT JOIN transactions t ON " \
                "        t.posted_date = s.posted_date AND " \
                "        t.amount = s.amount AND " \
                "        t.description = s.description " \
                "    WHERE t.id IS NULL;"
            if len(self.execute_query(check_dups)) != 0:
                log_msg = "No transactions inserted from staging, but NOT because all staged transactions were in db already"
                logger.error(log_msg)
                raise ValueError(log_msg)
            
        return len(rows_added)
    
    def get_balances_in_date_range(self, accnt_name: str, date_range: List[date]) -> List[Balance]:
        """
        Return balances in a date range for an account.
        
        Parameters
        ----------
        accnt_name : str
            Must exist in data_sources table as a name.
        date_range : List[date]
            List of length 2: beginning and end dates to return date for.
            Dates in datetime.date format

        Return
        ------
        List[Balance]
            List of balance dataclasses for all balances within date range
        """

        if len(date_range) != 2:
            log_msg = f"Date range must be list of length 2; got instead {date_range}"
            logger.error(log_msg)
            raise ValueError(log_msg)
        
        if (type(date_range[0]) != date) or (type(date_range[1]) != date):
            # date_range.sort() will do the wrong thing if this isn't date format
            log_msg = f"Date range must be in datetime.date format; got instead {date_range}"
            logger.error(log_msg)
            raise TypeError(log_msg)
        
        date_range.sort()

        col_names_str = ", ".join(BAL_COL_NAMES)

        bal_query = f"""
            SELECT {col_names_str}
            FROM balances
            WHERE balance_date BETWEEN %s AND %s
            AND accnt_id = (
                SELECT id
                FROM data_sources
                WHERE account_name=%s
                )
            ;
        """

        return self.execute_query_w_class(query=bal_query, return_class=Balance, vals=(date_range[0],date_range[1],accnt_name))
    
    def get_transactions_in_date_range(self, accnt_name: str, date_range: List[date]) -> List[Transaction]:
        """
        Return transactions in a date range for an account.
        
        Parameters
        ----------
        accnt_name : str
            Must exist in data_sources table as a name.
        date_range : List[date]
            List of length 2: beginning and end dates to return date for.
            Dates in datetime.date format

        Return
        ------
        List[Transaction]
            One Transaction for every entry in the specified range of dates
        """

        if len(date_range) != 2:
            log_msg = f"Date range must be list of length 2; got instead {date_range}"
            logger.error(log_msg)
            raise ValueError(log_msg)
        
        if (type(date_range[0]) != date) or (type(date_range[1]) != date):
            # date_range.sort() will do the wrong thing if this isn't date format
            log_msg = f"Date range must be in datetime.date format; got instead {date_range}"
            logger.error(log_msg)
            raise TypeError(log_msg)
        
        date_range.sort()

        col_names_str = ", ".join(f"t.{n}" for n in TRANS_COL_NAMES)

        trans_query = f"""
            SELECT {col_names_str}
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date BETWEEN %s AND %s
            AND s.account_name=%s;
        """

        return self.execute_query_w_class(query=trans_query, return_class=Transaction, vals=(date_range[0],date_range[1],accnt_name))
    
    # def get_uncategorized(self):
    #     """
    #     Return a csv of all transactions with no categorizations. 
    #     """
    
    # def update_categorizations(self, ...):
    #     """
    #     Given a csv of transactions and categorizations, update.
    #     Should this add new transactions if they're not already in db? probably yes?
    #     NOTE I'll have to change _import_file or make a new one to handle additional columns
    #     """


