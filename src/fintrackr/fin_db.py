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
import os
from typing import List

from datetime import date

from fintrackr.utils import Transaction, Col_Def, DEFAULT_LOGGING_FORMAT

logger = logging.getLogger(__name__)

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
    
    def execute_action(self, query: str) -> str:
        """
        Convenience function. Execute an action for which I want the response message, not a fetch.

        Calling function should handle expected exceptions via specific
        exception classes. No try-except block here.

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
            logger.info(f"Executing query: {query}")
            curs.execute(query)
            return curs.statusmessage
            
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
                        copy.set_types(["date", "float8", "text"]) # TODO should this not be hardcoded, if I'm not hard-coding dest_table?
                        for line in f:
                            copy.write(line) # TODO figure out the difference between write and write_row
                response = 1
            except Exception as e:
                logger.error(f"Failed to import from file {path_to_file} with exception: {e}")
            finally:
                return response

        
    def execute_query(self, query: str, vals: tuple = ()) -> List[tuple] | None:
        """
        Returns the result of a fetch to the database, after query execution.

        Calling function should handle expected exceptions (like violation of
        unique constraints if duplicates are attempted to be inserted) via specific
        exception classes. No try-except block here.

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)
            Args need to be passed in separately using %s in the query string
            (ie using parameterized SQL)
        vals: tuple
            Values, in order, for all %s's in the query string

        Returns
        -------
        List of tuples, or None
            result of fetchall if the SQL has a RETURNING clause, 
            or None if the query is malformed/table doesn't exist/no RETURNING
            Note to self: RETURNING in SQL returns a table; psycopg fetchall
            turns this into a tuple of rows

        """

        with self._conn.cursor() as curs: 
            logger.info(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.fetchall() # Returns a list of tuples (each row a tuple)
            
    def csv_to_staging(self, csv_path: str, csv_columns: List[Col_Def]) -> int:
        """ 
        FinTracker accepts csv inputs.
        Load csv from disk into a temporary staging table; caliing function loads from the
        staging table into the relevant permanent table(s) in the db.

        WILL OVERWRITE STAGING IF ALREADY EXISTS!

        Parameters
        ----------
        csv_path : str
            path to csv of transactions, balances, etc
        csv_columns : List[Col_Def]
            Columns in the csv which become columns in the staging table.
            Each element of the list is (col_name, col_type), eg ("posted date", "date")

        Returns
        -------
        int
            Length of a query of how many rows were added to the staging table

        """
        
        cols_placeholders = ', '.join('%s' for _ in csv_columns)

        # Drop staging table if it already exists
        # This set of logic feels goofy ... 
        rows_before = 0
        try:
            rows_before = self.execute_query(f"SELECT {cols_placeholders} FROM staging;", tuple([a.col_name for a in csv_columns]))
        except Exception as e:
            logger.debug(f"Query of staging table did not execute with exception: {e}")
        if rows_before is None:
            rows_before = 0
        if rows_before != 0:
            logger.info("Staging table still exists with content before loading new file")
            r = self.execute_action("DROP TABLE staging;")
            if r != "DROP TABLE":
                logger.error("Unable to drop staging table")
                raise ValueError("Unable to drop staging table before loading new file")
        
        col_and_type = ", ".join(f'{a} {b}' for a, b in csv_columns)
        r1 = self.execute_action(f"CREATE TABLE staging ({col_and_type}); ")
        if r1 != "CREATE TABLE":
            logger.error("Failed to create staging table")
            raise ValueError("Failed to create staging table before loading new file")

        r2 = self._import_file(dest_table="staging", path_to_file=csv_path)
        if r2==0: # This will happen if copy fails; eg if try to insert too many columns
            logger.info("No rows added to staging table")
            return 0

        # Query how many rows are now in staging table
        rows_after = self.execute_query(f"SELECT {cols_placeholders} FROM staging;", tuple([a.col_name for a in csv_columns]))
        logger.info(f"After loading new transactions, staging has {len(rows_after)} rows")

        return len(rows_after)
    
    def get_all_data_sources(self) -> list[str]:
        # Returns a list of data_sources names
        names_tuples = self.execute_query("SELECT name FROM data_sources;")
        # unpack the list of tuples into a list
        return [n for sublist in names_tuples for n in sublist]
    
    def get_data_source_id(self, source_name: str) -> int:
        return self.execute_query("SELECT id FROM data_sources WHERE name=%s;", (source_name,))
    
    def add_data_source(self, source_name: str) -> int:
        # Returns id after insertion
        return self.execute_query("INSERT INTO data_sources (name) VALUES (%s) RETURNING id;", (source_name,))

    def data_from_date_range(self, data_source: str, date_range: List[date]) -> dict[List[Transaction]]:
        """
        Get transactions and balances in a date range.

        Utility used by multiple other functions.
        
        Parameters
        ----------
        data_source : str
            Must exist in data_sources table as a name.
        date_range : List[date]
            List of length 2: beginning and end dates to return date for.
            Dates in datetime.date format

        Return
        ------
        dict[List[Transaction]]
            key = "transactions": All transactions (date, amount) with data_source_id = data_source and posted_dates
            in range(date_range)
            key = "balances": any account balances for this data_source in date_range
        """

        if len(date_range) != 2:
            logger.error(f"Date range must be list of length 2; got instead {date_range}")
            return None
        
        if (type(date_range[0]) != date) or (type(date_range[1]) != date):
            # date_range.sort() will do the wrong thing if this isn't date format
            logger.error(f"Date range must be in datetime.date format; got instead {date_range}")
            return None
        date_range.sort()

        trans_query = """
            SELECT t.posted_date, t.amount
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date BETWEEN %s AND %s
            AND s.name=%s;
        """

        trans = self.execute_query(trans_query, (date_range[0],date_range[1],data_source))
        transactions = [Transaction(date=d, amount=a) for d, a in trans]

        # All balances in date range
        bal_query = """
            SELECT date, amount
            FROM balances
            WHERE date BETWEEN %s AND %s
            AND accnt_id = (
                SELECT id
                FROM data_sources
                WHERE name=%s
                )
            ;
        """

        bals = self.execute_query(bal_query, (date_range[0],date_range[1],data_source))
        balances = [Transaction(date=d, amount=a) for d, a in bals]

        return {"transactions": transactions, "balances": balances}
    
    # def get_uncategorized(self):
    #     """
    #     Return a csv of all transactions with no categorizations. 
    #     """
    
    # def update_categorizations(self, ...):
    #     """
    #     Given a csv of transactions and categorizations, update.
    #     Should this add new transactions if they're not already in db? probably yes?
    #     """


