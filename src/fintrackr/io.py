"""
Utilities for basic file io.

Copyright (c) 2026 Stephanie Johnson
"""

import os
import pandas as pd
import logging

from typing import List

from fintrackr.utils import Col_Def, equiv_col_types, valid_date

logger = logging.getLogger(__name__)


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

    # Drop header if exists. We define a header as a row of all strings;
    # this will result in all columns being loaded as dtype objects.
    # Otherwise, given the numerical data FinTrackr expects, at least one column
    # should load as a float64.
    # ie. if there is a header, dtypes for all columns will be the same.
    # Extract header if it exists in case we can use it later.

    if f_input.dtypes.nunique() == 1: 
        # there is a header that we want to remove
        header = f_input.loc[0,:]
        f_mod = f_input.loc[1:, :].reset_index(drop=True)
    else:
        header = []
        f_mod = f_input.copy() # not great re: memory

    # We can tolerate more columns than we need, but we don't expect a particular order, so iterate through
    # and try to ID by data type (and header label if present). Raise error if we can't.
    # If there was a header, we have to re-infer new dtypes since everything will have been object

    if len(header) != 0:
        # I could re-load and re-infer using read_csv: 
        # f_mod.to_csv(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"), header=False, index=False, sep=",")
        # f_mod = pd.read_csv(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"), header=None)
        # os.remove(os.path.join(os.path.split(filepath)[0], filename+"_TEMP"+".csv"))
        # but since I think it's only the money column that would load as anything other than object:
        f_mod = f_mod.apply(pd.to_numeric, errors="ignore")

    c_keep = []
    for c in cols: # Iterate through the columns we're looking for
        for c_in in range(0, f_mod.shape[1]): # Check against the columns we have
            # Special cases we've encountered from particular bank outputs:
            # We know we're looking for dates, money, or a bank-assigned descrption of a transaction;
            # none of these are strings 0 or 1 length
            if len(str(f_mod.loc[0,c_in])) > 1:
                # pandas reads string columns as "objects"
                # See if we can extract a date from this column; 
                # otherwise assume object = string
                if str(f_mod[c_in].dtype) == 'object':
                    if valid_date(date_string = f_mod.loc[0,c_in]):
                        c_in_type = "date"
                    else:
                        c_in_type = "str"
                else:
                    c_in_type = str(f_mod[c_in].dtype)

                # Get info from header if we can    
                if len(header) != 0:
                    if header[c_in].strip().casefold() == c.col_name.casefold() and equiv_col_types(c_in_type, str(c.col_type)):
                        c_keep.append(c_in)
                        logger_msg = f"Keeping column with header {header[c_in]}" \
                                    f" from file {filepath} because name matches expected column {c.col_name}"\
                                    f" and column dtype {c_in_type} matches expected column type {c.col_type}"
                        logger.info(logger_msg)
                elif equiv_col_types(c_in_type, str(c.col_type)):
                    c_keep.append(c_in)
                    logger_msg = f"Keeping column {c_in}" \
                                f" from file {filepath}"\
                                f" because column dtype {c_in_type} matches expected column type {c.col_type}"
                    logger.info(logger_msg)

    if len(c_keep) < len(cols): # We couldn't identify enough columns as the ones we want
        logger.error(f"Could not identify correct columns from file {filepath}.")
        raise ValueError(f"Could not identify correct columns from file {filepath}.")
    
    if len(c_keep) != f_mod.shape[1] or len(header) != 0:
        f_final = f_mod.iloc[:,c_keep]
        new_filepath = potential_filepath
    
    # Save new file
    if len(new_filepath) != 0:
        f_final.to_csv(new_filepath, header=False, index=False, sep=",")

    return new_filepath


