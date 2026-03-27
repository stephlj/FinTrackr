"""
Utilities for basic file io.

Copyright (c) 2026 Stephanie Johnson
"""

import os
import pandas as pd
import logging
import re

from typing import List

from fintrackr.utils import Col_Def, equiv_col_types, valid_date

logger = logging.getLogger(__name__)

def col_type(col: pd.Series) -> str:
    """
    Try to identify data type in a column, where data type is specific
    to FinTrackr's expectations.

    Parameters
    ----------
    col : pd.Series
        Column from a df that's the result of loading a csv.
    
    Return
    ------
    str, column type or '' if not possible to determine.
        Return types will be one of {'date','text','money'}
        All elements in col must be the same type, else the return
        will be '' (not determined).
    """

    if sum(col.str.contains(r"\d+\.\d{2}",regex=True).notna()) == len(col) & sum(col.str.contains(r"\d+\.\d{2}",regex=True)) == len(col):
        return 'money'
    elif sum(col.apply(valid_date).notna()) == len(col) & sum(col.apply(valid_date)) == len(col):
        return 'date'
    elif sum(col.str.contains(r"[A-Za-z]+",regex=True).notna()) == len(col) & sum(col.str.contains(r"[A-Za-z]+",regex=True)) == len(col):
        return 'text'
    else:
        return ''


def strip_header(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Figure out whether a dataframe has a header.
    If so, remove it and re-infer float columns.
    Return modified (or original) df, and header if removed.
    If there was no header, header will be an empty series.
    
    Parameters
    ----------
    df : pandas dataframe
        Result of loading from a csv. 
    
    Returns
    -------
    pd.DataFrame, original or with header removed
    pd.Series, header or empty series if there was no header
    
    """

    # We define a header as a row of all strings;
    # this will result in all columns being loaded as dtype objects.
    # Otherwise, given the numerical data FinTrackr expects, at least one column
    # should load as a float64.
    # ie. if there is a header, dtypes for all columns will be the same.

    if df.dtypes.nunique() == 1: 
        # there is a header that we want to remove
        # Triple check that the first row is all text
        header = df.loc[0,:]
        if sum(header.str.contains(r"[A-Za-z]",regex=True).notna()) == len(header) & sum(header.str.contains(r"[A-Za-z]",regex=True)) == len(header):
            logger.info(f"Dropping header {header.astype(str).to_list()}")
            f_mod = df.loc[1:, :].reset_index(drop=True)
        else:
            logger.error(f"Can't ensure that first row {header.astype(str).to_list()} is a header")
            raise ValueError(f"Can't ensure that first row {header.astype(str).to_list()} is a header")
    else:
        header = pd.Series()
        f_mod = df
    
    # If there was a header, we have to re-infer new dtypes since everything will have been object
    if len(header) != 0:
        # I could re-load and re-infer using read_csv: 
        # f_mod.to_csv(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"), header=False, index=False, sep=",")
        # f_mod = pd.read_csv(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"), header=None)
        # os.remove(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"))
        # but since I think it's only the money column that would load as anything other than object:
        f_mod = f_mod.apply(pd.to_numeric, errors="ignore")

    return f_mod, header

def check_csv_format(filepath: str, cols: List[Col_Def]) -> str:
    """
    Transaction csvs downloaded from different banks have different formats - 
    soem have headers, some don't, some have more than the 3 columns we want
    (date, amount, description). 

    This function checks the format and saves a new csv with modified format if necessary.

    It also ensures no header for other csvs (e.g. balances).
    
    Parameters
    ----------
    filepath : str
        Path to a csv of transactions or balances.
    cols : List[Col_Def]
        For every expected column, provide the name as it would appear in a file header
        and type (see utils.SQL_to_python_types).
        Note that expected column order is important! - this will be expected import order into
        the db staging table.

    Returns
    -------
        Path to a new csv if modifications were made to the format.
        (Empty string if no mods were made).
    """

    new_filepath = ''
    filename = os.path.splitext(os.path.split(filepath)[-1])[0]
    potential_filepath = os.path.join(os.path.split(filepath)[0], filename+"_REFORMAT"+".csv") 

    f_input = pd.read_csv(filepath, header=None)

    # We can't do anything with too few columns:
    if f_input.shape[1] < len(cols):
        logger.error(f"Too few columns in file {filepath}; expected {len(cols)} columns, got {f_input.shape[1]}.")
        raise ValueError(f"Too few columns in file {filepath}.")
    
    f_mod, header = strip_header(f_input)

    # We can tolerate more columns than we need, but we don't expect a particular order, so iterate through
    # and try to ID by data type (and header label if present). Raise error if we can't.
    c_keep = []
    reorder = False
    for c in range(0,len(cols)): # Iterate through the columns we're looking for
        for c_in in range(0, f_mod.shape[1]): # Check against the columns we have
            c_in_type = col_type(f_mod.loc[:,c_in])
            if len(header) != 0:
                if header[c_in].strip().casefold() == cols[c].col_name.casefold() and c_in_type==cols[c].col_type:
                    c_keep.append(c_in)
                    if c != c_in:
                        reorder = True
                    logger_msg = f"Keeping column with header {header[c_in]}" \
                                f" from file {filepath} because name matches expected column {cols[c].col_name}"\
                                f" and column dtype {c_in_type} matches expected column type {cols[c].col_type}"
                    logger.info(logger_msg)
            elif c_in_type==cols[c].col_type:
                c_keep.append(c_in)
                if c != c_in:
                    reorder = True
                logger_msg = f"Keeping column {c_in}" \
                            f" from file {filepath}"\
                            f" because column dtype {c_in_type} matches expected column type {cols[c].col_type}"
                logger.info(logger_msg)

    if len(c_keep) != len(cols): # We couldn't identify the right number of columns as the ones we want
        logger.error(f"Could not identify correct columns from file {filepath}.")
        raise ValueError(f"Could not identify correct columns from file {filepath}.")
    
    if len(c_keep) != f_mod.shape[1] or len(header) != 0 or reorder:
        f_final = f_mod.iloc[:,c_keep]
        new_filepath = potential_filepath
    
    # Save new file
    if len(new_filepath) != 0:
        f_final.to_csv(new_filepath, header=False, index=False, sep=",")

    return new_filepath


