# fin_db.py
#
# Copyright (c) 2025 Stephanie Johnson
"""
Class that connects to the database and manages interactions with it
(adding transasctions, etc).

This is the database access layer; business logic should be elsewhere.

Copyright (c) 2025 Stephanie Johnson
"""

import psycopg
import logging
import os
import re

logger = logging.getLogger(__name__)

class FinDB:
    def __init__(self, user: str, pw: str, db_name: str = "fin_db"):
        self.user = user
        self.pw = pw
        self.db_name = db_name
        self._conn = psycopg.connect(f"dbname={self.db_name} user={self.user} password={self.pw} host='localhost'")
        self._conn.autocommit = True

    def __del__(self):
        try:
            self._conn.close()
        except Exception as e:
            # Ignore any erros during shutdown
            pass
    
    def _execute_action(self, query: str) -> str:
        """
        Convenience function. Execute an action for which I want the response message, not a fetch.

        Parameters
        ----------
        query : str
            SQL statement to execute

        Returns
        -------
        str
            conn.cursor.statusmessage

        I could wrap this in a transaction, but that's more opaque if something goes sideways,
        for non-prod situations like FinTrackr.

        For future reference, it would look something like:

        - BEGIN statement or run in ISOLATION_LEVEL_READ_COMMITTED or similar
        try:
            with self._cur ...
        except Exception as e:
            self._conn.rollback()
            raise e
        self._conn.commit()

        """
        # The with statement automatically closes cursor after execution
        with self._conn.cursor() as curs: 
            logger.info(f"Executing query {query}")
            curs.execute(query)
            response = curs.statusmessage
            logger.info(f"Completed with response {response}")
            return response
        
    def execute_query(self, query: str) -> tuple:
        """
        Returns the result of a query to the database.

        This feels like not great re: security/"little Johnny Tables" situations,
        so I'm forcing the query to be a SELECT statement only for now.

        Parameters
        ----------
        query : str
            SELECT statement to execute

        Returns
        -------
        tuple
            result of fetchall, or None if the query is malformed
            TODO what's the return if the query fails for a reason like the table doesn't exist

        """
        # The with statement automatically closes cursor after execution

        if query[0:5] != "SELECT":
            logger.error("FinDB.execute_query only accepts SELECT statements")
            return None

        with self._conn.cursor() as curs: 
            logger.info(f"Executing query {query}")
            curs.execute(query)
            response = curs.fetchall()
            return response

    def load_transactions(self, path_to_transactions: str) -> int:
        """ 
        FinTracker currently accepts csv inputs.
        Load csv from disk into a staging table, which we create if it doesn't already exist

        Parameters
        ----------
        path_to_transactions: str
            path to csv of transactions

        Returns
        -------
        int
            Length of a query of how many rows are now in staging table
            (should be length of rows added)

        """
        assert os.path.isfile(path_to_transactions), "FinDB._load_transactions: path_to_transactions not a path to a file"
        assert os.path.splitext(path_to_transactions)[1] == ".csv", "FinDB._load_transactions: path_to_transactions not a csv"

        create_staging = " CREATE TABLE IF NOT EXISTS staging( " \
            " Date date, Amount money, Description text); "
        
        # In case staging wasn't cleared:
        rows_before = self.execute_query("SELECT * FROM staging")
        if rows_before is not None:
            logger.debug(f"Before loading new transactions, staging has {len(rows_before)} rows")
        else:
            logger.debug(f"SELECT statement on staging table before loading transactions returns None")
        
        r1 = self._execute_action(create_staging)
        assert r1 == "CREATE TABLE", "Failed to create staging table"
        r2 = self._execute_action(f"COPY staging FROM '{path_to_transactions}' DELIMITERS ',' CSV;")
        r2_re = re.match("COPY "+r"\d+", r2)
        assert r2_re is not None

        # Query how many rows are now in staging table
        rows_after = self.execute_query("SELECT * FROM staging")
        logger.info(f"After loading new transactions, staging has {len(rows_after)-len(rows_before)} rows")

        return len(rows_after)-len(rows_before)

    # def add_metadata(self, ...)
    #     meta_query = "INSERT INTO data_load_metadata (date_added, username, source) VALUES () RETURNING id;"
    #     meta_id = self._execute_query(meta_query, ("data_load_metadata",))

    # def add_transactions(self, path_to_transactions: str) -> None:

    #     self._loadtransactions(path_to_transactions=path_to_transactions)

    #     self.add_metadata() # get FK

    #     trans_query = "INSERT INTO transactions (poasted_date, amount, description, metadatum_id) VALUES ()"
    #     success = self.cur.execute(trans_query, ("transactions",))
    
    #     # Remove all rows from staging table or drop table;
