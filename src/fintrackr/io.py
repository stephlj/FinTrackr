"""
Utilities for basic file io.

Copyright (c) 2026 Stephanie Johnson
"""

import os
import pandas as pd
import logging

from typing import List

from fintrackr.utils import Col_Def

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

    Returns
    -------
        Path to a new csv if modifications were made to the format.
        (Empty string if no mods were made).
    """

    new_filepath = ''

    f_input = pd.read_csv(filepath, header=None)

    # We can't do anything with too few columns:
    if f_input.shape[1] < len(cols):
        logger.error(f"Too few columns in file {filepath}; expected {len(cols)} columns, got {f_input.shape[1]}.")
        raise ValueError(f"Too few columns in file {filepath}.")

    # Drop header if exists. We define a header as a row of all strings;
    # this will result in all columns being loaded as dtype objects.
    # Otherwise, given the numerical data FinTrackr expects, at least one column
    # should load as a float64.
    # ie. if there is a header all dtypes will be the same.
    # Extract header if it exists in case we can use it later.
    
    header = [(f_input.iloc[0,0], str(f_input.dtypes[0]))] # start by assuming there is one

    for c in range(1,len(f_input.dtypes)):
        if str(f_input.dtypes[c]) != header[0][1]:
            # If we find just one mismatch, we know there's no header
            header = []
            f_mod = f_input.copy() # not great re: memory
            break
        else:
            header.append((f_input.iloc[0,c], str(f_input.dtypes[c])))

    if header != []:
        f_mod = f_input.loc[1:, :].reset_index(drop=True)
        # We'll need a new filepath
        filename = os.path.splitext(os.path.split(filepath)[-1])[0]
        new_filepath = os.path.join(os.path.split(filepath)[0], filename+"_REFORMAT"+".csv")
    
    
    # We can tolerate more columns than we need, but we don't expect a particular order, so iterate through
    # and try to ID by data type. Raise error if we can't.
    # TODO
    # For now, skip if there was a header - we won't have any actual info on datatypes?
    # Or can try to convert at least one to a date?

    # Save new file
    if len(new_filepath) != 0:
        f_mod.to_csv(new_filepath, header=False, index=False, sep=",")

    return new_filepath


