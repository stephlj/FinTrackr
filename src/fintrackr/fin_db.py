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
from typing import List

from datetime import date
from decimal import Decimal

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
            logger.info(f"Executing query: {query}")
            response = None
            try:
                curs.execute(query)
                response = curs.statusmessage
                logger.info(f"Completed with response {response}")
            except Exception as e:
                logger.exception(f"Query did not complete with exception: {e}")
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

        Parameters
        ----------
        query : str
            SELECT or INSERT statement to execute
            (something where the return should be the result of a fetchall, rather 
            than a status message)
            Args need to be passed in separately using %s in the query string
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

        response = None

        with self._conn.cursor() as curs: 
            logger.info(f"Executing query: {query}, with vals: {vals}")
            try:
                curs.execute(query, vals)
                response = curs.fetchall() # Returns a list of tuples (each row a tuple)
            except Exception as e:
                logger.debug(f"Query did not complete with exception: {e}")
                raise ValueError(f"Query did not complete with exception: {e}")
            finally:
                return response
            
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
            r = self._execute_action("DROP TABLE staging;")
            if r != "DROP TABLE":
                logger.error("Unable to drop staging table")
                raise ValueError("Unable to drop staging table before loading new file")
        
        col_and_type = ", ".join(f'{a} {b}' for a, b in csv_columns)
        r1 = self._execute_action(f"CREATE TABLE staging ({col_and_type}); ")
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

    
    def add_data_source(self, source_name: str) -> int:
        """
        Add source to data_source table if it doesn't exist.

        Parameters
        ----------
        source_name : str
        
        Returns:
        --------
        int, id of new data_source
        """
        # This can be done in one query but race conditions can occur, apparently
        source_name_tuple = self.execute_query("SELECT id FROM data_sources WHERE name=%s;", (source_name,))
        if len(source_name_tuple)==0:
           logger.info(f"Account name {source_name} doesn't exist; adding to table data_sources")
           source_name_tuple = self.execute_query("INSERT INTO data_sources (name) VALUES (%s) RETURNING id;", (source_name,))
           if source_name_tuple is None:
               logger.error(f"Could not insert new data source in data_sources table; query returned {source_name_tuple}")
               raise ValueError("Could not insert new data source in data_sources table")
        
        return source_name_tuple[0][0]


    def add_balance(self, accnt: str, bal_date: date, bal_amt: str) -> int:
        """
        Log a balance in the db. Will not allow exact duplicates to be added.

        Parameters
        ----------
        accnt: str
            Must exist in data_sources table as a name.
        bal_date : datetime.date
            Date that this was the account's balance.
        bal_amt : str
            Account balance on balance_date
        
        Return
        ------
        int, success (1) or not (0)
        """

        # Make sure bal_amt is formatted so it's recognized as money
        bal_amt = str(Decimal(bal_amt).quantize(Decimal('0.01')))

        accnt_id = self.add_data_source(source_name=accnt)

        try:
            rows_added = self.execute_query("INSERT INTO balances (accnt_id, date, amount) VALUES (%s, %s, %s) RETURNING *;", (accnt_id, bal_date, bal_amt))
        except Exception as e:
            logger.exception(f"Insertion into balances table failed with exception: {e}; return from query: {rows_added}")
            raise ValueError(f"Insertion into balances table failed with exception: {e}")
        
        if rows_added is not None:
            if len(rows_added) == 1:
                return 1
            else:
                logger.exception("Insertion into balances table returned something unexpected: {rows_added}")
                raise ValueError("Insertion into balances table returned something unexpected: {rows_added}")
        else:
            logger.info(f"No rows added to balances table; balance of {bal_amt} on date {bal_date} for account {accnt_id} may already exist")
            return 0
        
    def add_balances_from_csv(self, accnt: str, path_to_balances: str) -> int:
        """
        Load balances from csv into db.
        Will not allow duplicates to be added.

        Parameters
        ----------
        accnt: str
            Must exist in data_sources table as a name.
        path_to_balances : str
            Filepath to csv to load.
            Columns must be Date, Amount
        
        Return
        ------
        int
            Number of balances added
        """        

        num_new_balances = 0

        # Get id for this source_info or add if it doesn't exist
        accnt_id = self.add_data_source(source_name=accnt)

        staging_cols = [Col_Def(col_name="date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
        ]

        num_staged_balances = self.csv_to_staging(csv_path=path_to_balances, csv_columns=staging_cols)

        if num_staged_balances == 0:
            logger.info("No balances loaded from source file to staging table; no balances will be added to db")
            return num_new_balances
        
        balances_query = "INSERT INTO balances (date, amount, accnt_id) " \
            "SELECT date, amount, %s " \
            "FROM staging " \
            "RETURNING *;"
        
        try:
            all_new_balances = self.execute_query(balances_query, (accnt_id,))
        except Exception as e:
            logger.exception(f"Insertion into balances table failed with exception: {e}; return from query: {all_new_balances}")
            raise ValueError(f"Insertion into balances table failed with exception: {e}")
        
        self._execute_action("DROP TABLE staging;")
        
        if all_new_balances is not None:
            return len(all_new_balances)
        else:
            logger.info(f"No rows added to balances table; all balances in file {path_to_balances} may be in db")
            return 0

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

        staging_cols = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]

        num_staged_transactions = self.csv_to_staging(csv_path=path_to_source_file, csv_columns=staging_cols)

        if num_staged_transactions == 0:
            logger.info("No transactions loaded from source file to staging table; no transactions will be added")
            return num_new_transactions
        
        # Get id for this source_info or add if it doesn't exist
        source_info_id = self.add_data_source(source_info)

        today_date = date.today()
        
        transactions_query = "WITH joined AS ( " \
            "    SELECT s.* " \
            "    FROM staging s " \
            "    LEFT JOIN transactions t ON " \
            "        t.posted_date = s.posted_date AND " \
            "        t.amount = s.amount AND " \
            "        t.description = s.description " \
            "    WHERE t.id IS NULL " \
            "), " \
            "meta AS ( " \
            "    INSERT INTO data_load_metadata " \
            "        (date_added, username, source, data_source_id) " \
            "    VALUES (%s, %s, %s, %s)" \
            "    " \
            "    RETURNING id " \
            ") " \
            "INSERT INTO transactions (posted_date, amount, description, metadatum_id) " \
            "SELECT posted_date, amount, description, meta.id " \
            "FROM joined, meta " \
            "RETURNING *;"
            
        try:
            all_new_transactions = self.execute_query(transactions_query, (today_date, self.user, path_to_source_file, source_info_id))
        except Exception as e:
            logger.exception(f"Insertion into transactions table failed with exception: {e}; return from query: {num_new_transactions}")
            raise ValueError(f"Insertion into transactions table failed with exception: {e}")
        
        if all_new_transactions is None:
            logger.error("No transactions inserted")
            # Check if all new transactions to load are already in db and that's why it failed:
            check_dups = "SELECT s.* " \
                "    FROM staging s " \
                "    LEFT JOIN transactions t ON " \
                "        t.posted_date = s.posted_date AND " \
                "        t.amount = s.amount AND " \
                "        t.description = s.description " \
                "    WHERE t.id IS NULL;"
            if len(self.execute_query(check_dups)) == 0:
                logger.error("All staged transactions are already in transactions table")
                return 0
            else:
                raise ValueError("No transactions inserted, but not because all new transactions were in db already")

        # Drop staging table
        self._execute_action("DROP TABLE staging;")

        return len(all_new_transactions)
    
    def data_from_date_range(self, data_source: str, date_range: List[date]) -> dict[List[Transaction]]:
        """
        Return result of SELECT statement to the db as specified below.
        
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


