"""
Opens a connetion to the db and loads balances or transactions from csvs.

Copyright (c) 2026 Stephanie Johnson
"""

import yaml
import logging

from datetime import date
from psycopg import errors as psql_errors

import fintrackr.fin_db
from fintrackr.utils import CONFIG_PATH
from fintrackr.dataclasses import Col_Def
from fintrackr.io import check_csv_format, strip_header

BALS_STAGING_COLS = [Col_Def(col_name="date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
    ]

TRANS_STAGING_COLS = [Col_Def(col_name="posted_date", col_type="date"),
            Col_Def(col_name="amount", col_type="money"),
            Col_Def(col_name="description", col_type="text")
    ]

logger = logging.getLogger(__name__)
    
def add_balances(db_conn: object, accnt: str, path_to_balances: str) -> int:
    """
    Load balances from csv into db.
    Will not allow duplicates to be added.

    Parameters
    ----------
    db_conn : object
        FinDB object for db access
    accnt: str
        Account name to log balances for (name in data_sources)
    path_to_balances : str
        Filepath to csv to load.
        Columns must be Date, Amount (in that order)
    
    Return
    ------
    int
        Number of balances added. Zero if all balances to add were already in db.
    """        

    num_staged_balances = db_conn.csv_to_staging(csv_path=path_to_balances, csv_columns=BALS_STAGING_COLS)

    if num_staged_balances == 0:
        logger.info("No balances loaded from source file to staging table; no balances will be added to db")
        return 0
    
    try:
        num_new_balances = db_conn.add_balances_from_staging(accnt_name = accnt)
    except psql_errors.UniqueViolation as e:
        logger.info(f"Insertion into balances table under account {accnt} failed; all balances are already in the db (exception: {e})")
        return 0
    except psql_errors.NotNullViolation as e:
        logger.error(f"Insertion into balances table failed with exception {e}; check account name {accnt} exists in db")
        raise
    except Exception as e:
        logger.exception(f"Insertion into balances table failed with exception: {e}")
        raise
    
    # I could put this in a finally clause, but that makes debugging harder. csv_to_staging will clear it if it exists
    db_conn.execute_action("DROP TABLE staging;")
    
    return num_new_balances

def add_transactions(db_conn: object, path_to_source_file: str, source_info: int) -> None:
    """
    Load transactions from a file and log the addition of these transactions
    in the data_load_metadata table.

    Only new transactions are added; duplicates (which have identity across the 3
    input columns of Date, Amount, and Description with an existing transaction row)
    are ignored.

    Parameters
    ----------
    db_conn: object
        FinDB object that manages db access.
    path_to_source_file: str
        Path to a csv where every row is a transaction.
    source_info: int
        id of an account in data_sources

    Returns
    -------
    int
        Number of transactions added.
    """

    num_new_transactions = 0

    num_staged_transactions = db_conn.csv_to_staging(csv_path=path_to_source_file, csv_columns=TRANS_STAGING_COLS)

    if num_staged_transactions == 0:
        logger.info("No transactions loaded from source file to staging table; no transactions will be added")
        return num_new_transactions
        
    try:
        num_new_transactions = db_conn.add_transactions_from_staging(path_to_source_file=path_to_source_file, source_info=source_info)
    except psql_errors.NotNullViolation as e:
        logger.error(f"Insertion into transactions table failed with null violation (exception: {e}); check account name {source_info} exists in db")
        raise
    except psql_errors.UniqueViolation as e:
        logger.info(f"Insertion of {path_to_source_file} data into transactions table under account {source_info} failed; file may already have been loaded (exception: {e})")
        return 0
    except Exception as e:
        logger.exception(f"Insertion into transactions table failed with exception: {e}")
        raise
    
    if num_new_transactions == 0:
        logger.info("All staged transactions are already in transactions table")
            
    # Drop staging table
    db_conn.execute_action("DROP TABLE staging;")

    return num_new_transactions

def load_data_from_CLI(accnt_name: str, 
                       filepath: str, 
                       username: str, 
                       pw: str, 
                       trans: bool, 
                       add_as_new_acct = False, 
                       db_config: str = '') -> None:
    """
    
    Load transactions or balances from csv file into db.


    Parameters
    ----------
    accnt_name : str
        Which account are these balances or transactions for?
        Equivalent to name column in data_sources
    filepath : str
        Path to a csv file to load.
    username : str
        User to use to connect to db
    pw : str
        User's pw to connect to db
    trans : bool, default False
        If true, these are transactions. If false, they are balances.
    add_as_new_acct : bool
        If add_as_new_acct is True, it will add accnt_name to data_sources.
        If accnt_name doesn't exist and add_as_new_acct is False, it will error out.
        If accnt_name DOES exist and add_as_new_acct is True, it will error out.
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

    db_conn = fintrackr.fin_db.FinDB(user=username, pw=pw, db_name=db_name)
    
    if add_as_new_acct:
        try:
            _ = db_conn.add_data_source(source_name=accnt_name)
            logger.info(f"Added account name {accnt_name} as new data source")
        except psql_errors.UniqueViolation as e:
            log_msg = f"Account name {accnt_name} already exists!"
            logger.error(log_msg)
            raise ValueError(log_msg)
    else:
        # Check account exists
        source_id_tuple = db_conn.get_data_source_id(source_name=accnt_name)
        if len(source_id_tuple)==0:
            # User didn't want to add a new account, but this one doesn't exist
            existing_sources = db_conn.get_all_data_sources()
            log_msg = f"Account name {accnt_name} doesn't exist; did you mean one of {existing_sources} instead?"
            logger.error(log_msg)
            raise ValueError(log_msg)          
    
    if trans:
        result = add_transactions(
                db_conn = db_conn,
                path_to_source_file = filepath, 
                source_info = accnt_name
                )
    else:
        result = add_balances(
            db_conn=db_conn, 
            accnt = accnt_name, 
            path_to_balances=filepath
            )

    db_conn.close()

    if result >= 1:
        logger.info(f"Successfully logged data from file {filepath} in {db_name} under account {accnt_name}")
    else:
        logger.info(f"Unsuccessful attempt to log data from file {filepath} in {db_name} under account {accnt_name}")