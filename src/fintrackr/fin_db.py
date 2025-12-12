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

logger = logging.getLogger(__name__)

class FinDB:
    def __init__(self, user: str, name: str = "fin_db"):
        self._conn = psycopg.connect(f"dbname={name} user={user}")
        self._cur = self._conn.cursor()

    def _execute_query(self, query: str) -> list:
        """
        Convenience function.

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
        with self._cur as curs: 
            logger.info(f"Executing query {query}")
            curs.execute(query)
            response = curs.fetchall()
            logger.info(f"Completed with response {response}")
            return response

    def _load_transactions(self, path_to_transactions: str) -> None:
        """ 
        FinTracker currently accepts csv inputs.
        Load csv from disk into a staging table, which we create if it doesn't already exist

        Parameters
        ----------
        path_to_transactions: str
            path to csv of transactions

        Returns
        -------
        None, though it should probably return the query response

        """
        assert os.path.isfile(path_to_transactions), "FinDB._load_transactions: path_to_transactions not a path to a file"
        assert os.path.splitext(path_to_transactions)[1] == ".csv", "FinDB._load_transactions: path_to_transactions not a csv"

        create_staging = " CREATE TABLE IF NOT EXISTS staging( " \
            " Date date, Amount money, Description text) "
        
        response1 = self._execute_query(create_staging)
        response2 = self._execute_query(f"COPY staging FROM '{path_to_transactions}' DELIMITERS ',' CSV ")

    def _add_metadata(self, ...)
        meta_query = "INSERT INTO data_load_metadata (date_added, username, source) VALUES () RETURNING id"
        meta_id = self.cur.execute(meta_query, ("data_load_metadata",))

    def add_transactions(self, path_to_transactions: str) -> None:

        self._load_transactions(path_to_transactions=path_to_transactions)

        self._add_metadata() # get FK

        trans_query = "INSERT INTO transactions (poasted_date, amount, description, metadatum_id) VALUES ()"
        success = self.cur.execute(trans_query, ("transactions",))
    
        # Remove all rows from staging table or drop table