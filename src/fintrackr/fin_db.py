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

import pandas as pd # temporary, till I move some logic elsewhere

logger = logging.getLogger(__name__)
DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

class FinDB:
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)

    def __init__(self, user: str, pw: str, db_name: str = "fin_db"):
        self.user = user
        self.pw = pw
        self.db_name = db_name
        self._conn = psycopg.connect(f"dbname={self.db_name} user={self.user} password={self.pw} host='localhost'")
        self._conn.autocommit = True

    def close(self):
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
            response = None
            try:
                curs.execute(query)
                response = curs.statusmessage
                logger.info(f"Completed with response {response}")
            except Exception as e:
                logger.error(f"Query did not complete with exception: {e}")
            finally:
                return response
        
    def execute_query(self, query: str) -> tuple:
        """
        Returns the result of a query to the database.

        This feels like not great re: security/"little Johnny Tables" situations,
        so I'm forcing the query to be a SELECT statement only for now. (Not that
        that prevents Little Johnny Tables ... TODO switch to parameterized SQL)

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

        response = None

        if query[0:6] != "SELECT".upper(): # goofy!
            logger.error("FinDB.execute_query only accepts SELECT statements")
            return response

        with self._conn.cursor() as curs: 
            logger.info(f"Executing query {query}")
            try:
                curs.execute(query)
                response = curs.fetchall() # Returns a list of tuples (each row a tuple)
            except Exception as e:
                logger.debug(f"Query did not complete with exception: {e}")
            finally:
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
            Length of a query of how many rows were added to the staging table

        """
        assert os.path.isfile(path_to_transactions), "FinDB._load_transactions: path_to_transactions not a path to a file"
        assert os.path.splitext(path_to_transactions)[1] == ".csv", "FinDB._load_transactions: path_to_transactions not a csv"

        create_staging = " CREATE TABLE IF NOT EXISTS staging( " \
            " Date date, Amount money, Description text); "
        
        # TODO move this to business logic layer
        # Check that the input conforms to expectations
        # input = pd.read_csv(path_to_transactions, dtype=str, header=None)
        # assert input.shape[1] >= 3 # there can be extra columns, we'll ignore those
        # input_types = input.dtypes
        # assert input_types[1] == float, "Second column must be a float (amount)"
        # TODO how to check the other columns?
        
        # In case staging wasn't cleared: should I clear it?
        query_staging = "SELECT * FROM staging"
        rows_before = self.execute_query(query_staging)
        if rows_before is not None:
            logger.debug(f"Before loading new transactions, staging has {len(rows_before)} rows")
        else:
            rows_before = []
            logger.debug(f"SELECT statement on staging table before loading transactions returns None")
        
        r1 = self._execute_action(create_staging)
        assert r1 == "CREATE TABLE", "Failed to create staging table"
        r2 = self._execute_action(f"COPY staging FROM '{path_to_transactions}' DELIMITERS ',' CSV;")
        if r2 is None: # This will happen if copy fails; eg if try to insert too many columns
            logger.info("No rows added to staging table")
            return 0
        r2_re = re.match("COPY "+r"\d+", r2)
        assert r2_re is not None

        # Query how many rows are now in staging table
        rows_after = self.execute_query(query_staging)
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
    # TODO how to check that duplicates weren't added?
