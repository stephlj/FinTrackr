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
        vals: Tuple
            Values, in order, for all %s's in the query string

        Returns
        -------
        List of tuples, or None
            result of fetchall if the SQL has a RETURNING clause, 
            or None if the query is malformed/table doesn't exist/no RETURNING

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


    def add_balance(self, accnt: str, bal_date: date, bal_amt: float) -> int:
        """
        Log a balance in the db.

        Parameters
        ----------
        accnt: str
            Must exist in data_sources table as a name.
        bal_date : datetime.date
            Date that this was the account's balance.
        bal_amt : float
            Account balance on balance_date
        
        Return
        ------
        int, success (1) or not (0)
        """

        accnt_id = self.add_data_source(source_name=accnt)

        try:
            rows_added = self.execute_query("INSERT INTO balances (accnt_id, date, amount) VALUES (%s, %s, %s) RETURNING *;", (accnt_id, bal_date, str(bal_amt)))
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
            return 0

    
    def stage_transactions(self, path_to_transactions: str) -> int:
        """ 
        FinTracker currently accepts csv inputs.
        Load csv from disk into a temporary staging table, which will then go into
        the transactions table in the db (executed in a separate function).

        Parameters
        ----------
        path_to_transactions: str
            path to csv of transactions

        Returns
        -------
        int
            Length of a query of how many rows were added to the staging table

        """

        # TODO move this to business logic layer
        # Check that the input conforms to expectations
        # input = pd.read_csv(path_to_transactions, dtype=str, header=None)
        # assert input.shape[1] >= 3 # there can be extra columns, we'll ignore those
        # input_types = input.dtypes
        # assert input_types[1] == float, "Second column must be a float (amount)"
        # TODO how to check the other columns?
        
        # Drop staging table if it already exists
        # This set of logic feels goofy ... 
        rows_before = 0
        try:
            rows_before = self.execute_query("SELECT posted_date, amount, description FROM staging;")
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
        
        create_staging = " CREATE TABLE staging( " \
            " posted_date date, amount money, description text); "
        r1 = self._execute_action(create_staging)
        if r1 != "CREATE TABLE":
            logger.error("Failed to create staging table")
            raise ValueError("Failed to create staging table before loading new file")

        r2 = self._import_file(dest_table="staging", path_to_file=path_to_transactions)
        if r2==0: # This will happen if copy fails; eg if try to insert too many columns
            logger.info("No rows added to staging table")
            return 0

        # Query how many rows are now in staging table
        rows_after = self.execute_query("SELECT posted_date, amount, description FROM staging;")
        logger.info(f"After loading new transactions, staging has {len(rows_after)} rows")

        return len(rows_after)

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

        num_staged_transactions = self.stage_transactions(path_to_transactions = path_to_source_file)

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
        
        num_new_transactions = len(all_new_transactions)

        # Drop staging table
        self._execute_action("DROP TABLE staging;")

        return num_new_transactions
    
    # def get_uncategorized(self):
    #     """
    #     Return a csv of all transactions with no categorizations. 
    #     """
    
    # def update_categorizations(self, ...):
    #     """
    #     Given a csv of transactions and categorizations, update.
    #     Should this add new transactions if they're not already in db? probably yes?
    #     """


