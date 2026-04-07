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

from fintrackr.dataclasses import Transaction, Balance, Col_Def
from fintrackr.utils import DEFAULT_LOGGING_FORMAT

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
            logger.exception("FinDB object failed to close")
            pass
    
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
    
    def execute_action(self, query: str, vals: tuple = ()) -> str:
        """
        Convenience function. Execute an action for which I want the response message, not a fetch.

        Calling function should handle expected exceptions via specific
        exception classes. No try-except block here.

        Parameters
        ----------
        query : str
            SQL statement to execute
        vals: tuple
            Values, in order, for any/all %s's in the query string

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
            logger.info(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            return curs.statusmessage

        
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
        
    def execute_scalar(self, query: str, vals: tuple = ()) -> int | str | None:
        """
        Returns the result of a fetch to the database, after query execution.

        Assumes single return (will error if the query returns multiple rows).

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
        int | str

        """

        with self._conn.cursor() as curs: 
            logger.info(f"Executing query: {query}, with vals: {vals}")
            curs.execute(query, vals)
            row_tuple = curs.fetchall() # Returns a list of tuples (each row a tuple)
        
        if len(row_tuple) != 1:
            log_msg = f"Query: {query} with vals: {vals} did not return a single row as expected"
            logger.error(log_msg)
            raise ValueError(log_msg)
        
        if len(row_tuple[0]) != 1:
            log_msg2 = f"Query: {query} with vals: {vals} did not return a single item as expected"
            logger.error(log_msg2)
            raise ValueError(log_msg2)
        
        return row_tuple[0][0]
            
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
            # TODO add an execute_scalar method, if I find myself wanting to do this a lot
            rows_before = self.execute_scalar("SELECT COUNT(*) FROM staging;")
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
        rows_after = self.execute_scalar("SELECT COUNT(*) FROM staging;")
        logger.info(f"After loading new transactions, staging has {rows_after} rows")

        return rows_after
    
    def get_all_data_sources(self) -> list[str]:
        # Returns a list of data_sources names
        names_tuples = self.execute_query("SELECT name FROM data_sources;")
        # unpack the list of tuples into a list
        return [n for sublist in names_tuples for n in sublist]
    
    def get_data_source_id(self, source_name: str) -> int:
        return self.execute_scalar("SELECT id FROM data_sources WHERE name=%s;", (source_name,))
    
    def add_data_source(self, source_name: str) -> int:
        # Returns id after insertion
        return self.execute_scalar("INSERT INTO data_sources (name) VALUES (%s) RETURNING id;", (source_name,))
    
    def add_balances_from_staging(self, accnt_name: str) -> int:
        # Insert balances that are in a staging table into the balances table of the db, under accnt_name.
        # Return number of inserted rows.
        # Will return an empty list if (date, amount) already exists (violation of that unique constraint)
        # and a NotNullViolation exception if accnt_name isn't already in data_sources
        
        balances_query = "INSERT INTO balances (date, amount, accnt_id) " \
            "SELECT s.date, s.amount, (select id from data_sources where name = %s) " \
            "FROM staging AS s " \
            "RETURNING *;"
        
        # For reference, another way of doing the same thing:
        # balances_query = "INSERT INTO balances (date, amount, accnt_id) " \
        #     "SELECT s.date, s.amount, d.id " \
        #     "FROM staging AS s " \
        #     "CROSS JOIN data_sources AS d WHERE name = %s "\
        #     "RETURNING *;"
        # However this just returns an empty list if name doesn't exist, rather than a NotNullViolation, so
        # preferring the first version (see commented out code below to raise the error I would want)

        rows_added = self.execute_query(balances_query, (accnt_name,))

        # if len(rows_added) == 0 and len(self.get_data_source_id(accnt_name)) == 0:
        #     raise psycopg.errors.NotNullViolation(f"Account {accnt_name} does not exist; cannot add balances for that account")

        return len(rows_added)
    
    def add_transactions_from_staging(self, path_to_source_file: str, source_info: str) -> int:
        # Insert transactions that are in a staging table into the transactions table of the db.
        # Return number of inserted rows. Returns zero if all transactions in staging are already in db.

        # Log that these transactions were added today in the metadata table
        today_date = date.today()

        # Option 1:
        source_id_tuple = self.get_data_source_id(source_info)
        if len(source_id_tuple) == 0:
            raise psycopg.errors.NotNullViolation(f"Account {source_info} does not exist; cannot add transactions for that account")
        source_id = source_id_tuple[0][0]
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

        bals = self.execute_query(bal_query, (date_range[0],date_range[1],accnt_name))

        return [Balance(date=d, amount=a) for d, a in bals]
    
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

        trans_query = """
            SELECT t.posted_date, t.amount, t.description
            FROM transactions AS t
            JOIN data_load_metadata AS m ON m.id = t.metadatum_id
            JOIN data_sources AS s ON s.id = m.data_source_id
            WHERE t.posted_date BETWEEN %s AND %s
            AND s.name=%s;
        """

        trans = self.execute_query(trans_query, (date_range[0],date_range[1],accnt_name))
        return [Transaction(date=d, amount=a, description=s) for d, a, s in trans]
    
    # def get_uncategorized(self):
    #     """
    #     Return a csv of all transactions with no categorizations. 
    #     """
    
    # def update_categorizations(self, ...):
    #     """
    #     Given a csv of transactions and categorizations, update.
    #     Should this add new transactions if they're not already in db? probably yes?
    #     """


