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
from datetime import date

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
            
    def _import_file(self, dest_table: str, path_to_file: str) -> int:
        """
        To avoid granting permission to read server files, I use a client-side copy
        This function wraps that copy command.
        
        Parameters
        ----------
        dest_table: str
            Name of table to copy into (should already exist)
        path_to_file: str
            Path to file whose contents are to be copied. Must be a csv.
        
        Returns
        -------
        int:
            1 if successful copy, 0 if an exception occurred

        """
        response = 0 # assume failure :)

        if not os.path.isfile(path_to_file):
            logger.error(f"FinDB._import_file: {path_to_file} not a path to a file that exists")
            return response
        if not os.path.splitext(path_to_file)[1] == ".csv":
            logger.error(f"FinDB._import_file: {path_to_file} not a csv")
            return response

        with self._conn.cursor() as curs: 
            logger.info(f"Importing from file {path_to_file}")
            try:
                with open(path_to_file, "r") as f:
                    with curs.copy(f"COPY {dest_table} FROM STDIN WITH (FORMAT csv, HEADER false)") as copy:
                        copy.set_types(["date", "float8", "text"]) # TODO I'm not sure this is working correctly, check
                        for line in f:
                            copy.write(line) # TODO figure out the difference between write and write_row
                response = 1
            except Exception as e:
                logger.error(f"Failed to import from file {path_to_file} with exception: {e}")
            finally:
                return response

        
    def execute_query(self, query: str) -> tuple:
        """
        Returns the result of a query to the database.

        This is not great re: security/"little Bobby Tables" situations.
        TODO use parameterized SQL to fix.

        TODO Should I have different methods for SELECT (doesn't alter db data)
        vs INSERT (does alter db data)? And make INSERT an internal method perhaps?

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)

        Returns
        -------
        tuple
            result of fetchall, or None if the query is malformed
            TODO what's the return if the query fails for a reason like the table doesn't exist

        """

        response = None

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

        create_staging = " CREATE TABLE IF NOT EXISTS staging( " \
            " posted_date date, amount money, description text); "
        
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

        r2 = self._import_file(dest_table="staging", path_to_file=path_to_transactions)
        if r2==0: # This will happen if copy fails; eg if try to insert too many columns
            logger.info("No rows added to staging table")
            return 0

        # Query how many rows are now in staging table
        rows_after = self.execute_query(query_staging)
        logger.info(f"After loading new transactions, staging has {len(rows_after)-len(rows_before)} rows")

        return len(rows_after)-len(rows_before)

    def add_transactions(self, path_to_source_file: str, source_info: str) -> None:
        """
        Load transactions from a file and log the addition of these transactions
        in the data_load_metadata table.

        Only new transactions are added; duplicates (which have identity across the 3
        input columns of Date, Amount, and Description with an existing transaction row)
        are ignored.

        Parameters
        ----------
        path_to_source_file: str
            Path to a csv where every row is a transaction.
        source_info: str
            Are these transactions from credit card, checking account, etc
            This is the "name" field in the data_sources table.
            It will be added if it doesn't already exist.

        Returns
        -------
        int
            Number of transactions added.
        """
        num_new_transactions = 0

        num_staged_transactions = self.load_transactions(path_to_transactions = path_to_source_file)

        if num_staged_transactions == 0:
            logger.info("No transactions loaded from source file to staging table; no transactions will be added")
            return num_new_transactions
        
        # Get id for this source_info, if it exists
        # This can be done in one query but race conditions can occur
        source_info_id = self.execute_query(f"SELECT id FROM data_sources WHERE name='{source_info}';")
        if source_info_id is None:
           logger.info(f"Data source {source_info} doesn't exist; adding to data_sources table")
           source_info_id = self.execute_query(f"INSERT INTO data_sources (name) VALUES ('{source_info}' RETURNING id);")
           if source_info_id is None:
               raise ValueError("Could not insert new data source in data_sources table")
        
        transactions_query = f"WITH joined AS ( " \
            "    SELECT	s.* " \
            "    FROM	staging s " \
            "    LEFT JOIN transactions t ON " \
            "        t.posted_date = s.posted_date AND " \
            "        t.amount = s.amount AND " \
            "        t.description = s.description " \
            "    WEHRE	t.id IS NULL " \
            "), " \
            "meta AS ( " \
            "    INSERT INTO data_load_metadata " \
            "        (date_added, username, source, data_source_id) " \
            "    VALUES ('{date.today}', '{self.user}', '{path_to_source_file}', '{source_info}')" \
            "    " \
            "    RETURNING id " \
            ") " \
            "INSERT INTO transactions (posted_date, amount, description, metadatam_id) " \
            "SELECT	posted_date, amount, description, meta.id " \
            "FROM joined, meta; " \
            
        num_new_transactions = self.execute_query(transactions_query) # This returns the result of the final INSERT statement
        
        # Drop staging table
        self._execute_action("DROP TABLE staging;")

        return num_new_transactions
    
    # def update_categorizations(self, ...):
    #     """
    #     Should probably have a separate function that gets uncategorized transactions?
    #     """


