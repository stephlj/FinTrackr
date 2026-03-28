"""
Opens a connetion to the db and loads balances or transactions from csvs.

Copyright (c) 2026 Stephanie Johnson
"""

import yaml
import logging

from datetime import date
from decimal import Decimal
from psycopg import errors as psql_errors # psql_errors.UniqueViolation

import fintrackr.fin_db
from fintrackr.utils import CONFIG_PATH, Col_Def
from fintrackr.io import check_csv_format, strip_header

BALS_STAGING_COLS = [Col_Def(col_name="date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
    ]

TRANS_STAGING_COLS = [Col_Def(col_name="posted_date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
            Col_Def(col_name="description", col_type="text")
    ]

logger = logging.getLogger(__name__)

def get_or_add_data_source(db_conn: object, source_name: str) -> int:
        """
        Add source to data_source table if it doesn't exist, and return id.

        Utility used in multiple places; data source means source of a csv file to load
        (was it downloaded from primary checking, etc); this is equivalent to adding an account
        (since accounts are data sources). Data source and accounts are used interchangeably in the BLL.

        Parameters
        ----------
        db_conn : FinDB object
            Object that handles db connection
        source_name : str
            Account name (e.g. "primary checking")
        
        Returns:
        --------
        int, id of new data_source
            Will be added if doesn't exist in db
        """
        
        source_id_tuple = db_conn.get_data_source_id(source_name=source_name)
        if len(source_id_tuple) == 0:
            logger.info(f"Account name {source_name} doesn't exist; adding to table data_sources")
            source_id_tuple = db_conn.add_data_source(source_name=source_name)
        else:
            logger.debug(f"Account name {source_name} exists, returning existing id")
        
        return source_id_tuple[0][0]

def add_balance(FinDB: object, accnt: str, bal_date: date, bal_amt: str) -> int:
    """
    Log a balance in the db. Will not allow exact duplicates to be added.

    Parameters
    ----------
    FinDB : object
        FinDB object for db access
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

    accnt_id = FinDB.get_or_add_data_source(source_name=accnt)

    try:
        rows_added = FinDB.execute_query("INSERT INTO balances (accnt_id, date, amount) VALUES (%s, %s, %s) RETURNING *;", (accnt_id, bal_date, bal_amt))
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
    
def add_balances_from_csv(FinDB: object, accnt: str, path_to_balances: str) -> int:
    """
    Load balances from csv into db.
    Will not allow duplicates to be added.

    Parameters
    ----------
    FinDB : object
        FinDB object for db access
    accnt: str
        Must exist in data_sources table as a name.
    path_to_balances : str
        Filepath to csv to load.
        Columns must be Date, Amount (in that order)
    
    Return
    ------
    int
        Number of balances added
    """        

    num_new_balances = 0

    accnt_id = FinDB.get_or_add_data_source(source_name=accnt)

    num_staged_balances = FinDB.csv_to_staging(csv_path=path_to_balances, csv_columns=BALS_STAGING_COLS)

    if num_staged_balances == 0:
        logger.info("No balances loaded from source file to staging table; no balances will be added to db")
        return num_new_balances
    
    balances_query = "INSERT INTO balances (date, amount, accnt_id) " \
        "SELECT date, amount, %s " \
        "FROM staging " \
        "RETURNING *;"
    
    try:
        all_new_balances = FinDB.execute_query(balances_query, (accnt_id,))
    except Exception as e:
        logger.exception(f"Insertion into balances table failed with exception: {e}; return from query: {all_new_balances}")
        raise ValueError(f"Insertion into balances table failed with exception: {e}")
    
    FinDB.execute_action("DROP TABLE staging;")
    
    if all_new_balances is not None:
        return len(all_new_balances)
    else:
        logger.info(f"No rows added to balances table; all balances in file {path_to_balances} may be in db")
        return 0

def add_transactions(FinDB: object, path_to_source_file: str, source_info: str) -> None:
    """
    Load transactions from a file and log the addition of these transactions
    in the data_load_metadata table.

    Only new transactions are added; duplicates (which have identity across the 3
    input columns of Date, Amount, and Description with an existing transaction row)
    are ignored.

    Parameters
    ----------
    FinDB: object
        FinDB object that manages db access.
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

    num_staged_transactions = FinDB.csv_to_staging(csv_path=path_to_source_file, csv_columns=TRANS_STAGING_COLS)

    if num_staged_transactions == 0:
        logger.info("No transactions loaded from source file to staging table; no transactions will be added")
        return num_new_transactions
    
    source_info_id = FinDB.get_or_add_data_source(source_info)

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
        all_new_transactions = FinDB.execute_query(transactions_query, (today_date, FinDB.user, path_to_source_file, source_info_id))
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
        if len(FinDB.execute_query(check_dups)) == 0:
            logger.error("All staged transactions are already in transactions table")
            return 0
        else:
            raise ValueError("No transactions inserted, but not because all new transactions were in db already")

    # Drop staging table
    FinDB.execute_action("DROP TABLE staging;")

    return len(all_new_transactions)

def load_data_from_CLI(accnt_name: str, filepath: str, username: str, pw: str, trans: bool, db_config: str = '') -> None:
    """
    
    Load transactions or balances from csv file into db.

    Parameters
    ----------
    accnt_name : str
        Which account are these balances or transactions for?
        Equivalent to name column in data_sources (will be added if doesn't exist in that table)
    filepath : str
        Path to a csv file to load.
    username : str
        User to use to connect to db
    pw : str
        User's pw to connect to db
    trans : bool
        If true, these are transactions. If false, they are balances.
    db_config : str, optional
        path to config file for db.
        Will use default in utils if not specified.

    Returns
    -------
    None
    """
    
    if db_config=='':
        db_config = CONFIG_PATH

    with open(db_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        if trans:
            date_headers = config["transaction_headers"][[x.col_name for x in TRANS_STAGING_COLS if x.col_type=='date'][0]]
            amount_headers = config["transaction_headers"][[x.col_name for x in TRANS_STAGING_COLS if x.col_type=='money'][0]]
            desc_headers = config["transaction_headers"][[x.col_name for x in TRANS_STAGING_COLS if x.col_type=='text'][0]]

    # Clean input if necessary
    # Enumerate all possible input column combos for transactions:
    if trans:
        expect_cols = []
        for d in date_headers:
            for a in amount_headers:
                for c in desc_headers:
                    # Note order matters here!
                    # check_csv_format will reorder columns to match this spec.
                    # So this spec must match the order expected when csv contents
                    # are loaded into the staging table in csv_to_staging().
                    expect_cols.append([Col_Def(col_name=d, col_type=TRANS_STAGING_COLS[0].col_type),
                                        Col_Def(col_name=a, col_type=TRANS_STAGING_COLS[1].col_type),
                                        Col_Def(col_name=c, col_type=TRANS_STAGING_COLS[2].col_type)
                                ])
    else:
        # We insist on this format since it's user-provided rather than bank provided
        expect_cols = [BALS_STAGING_COLS]
    
    success = False
    for c in expect_cols:
        try:
            new_path = check_csv_format(filepath=filepath, cols=c)
            success = True
        except:
            pass
        if success:
            break

    if not success:
        logger.error("Unable to load data from file {filepath}")
        raise ValueError("Unable to load data from file {filepath}")

    if len(new_path) != 0:
        # Switch to modified file with corrected format
        filepath = new_path

    FinDB = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)
    
    if trans:
        result = add_transactions(
                FinDB = FinDB,
                path_to_source_file = filepath, 
                source_info = accnt_name
                )
    else:
        result = add_balances_from_csv(
            FinDB=FinDB, 
            accnt = accnt_name, 
            path_to_balances=filepath
            )

    FinDB.close()

    if result >= 1:
        logger.info(f"Successfully logged data from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log data from file {filepath} in {db_name} under account {accnt_name}")