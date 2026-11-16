"""
Since we don't control the format of bank-provided inputs, and accept several
formats, wrangle them into a standardized input for FinTrackr here.

Main entry is reformat_csv. A new version of each input is saved for manual checking
and logging.

Copyright (c) 2026 Stephanie Johnson
"""

import os
import csv
import yaml
import logging
import re

from dataclasses import fields
from typing import NamedTuple

from dbcommons.utils import check_csv_path
from fintrackr.fin_dataclasses import TRANS_COL_NAMES, Transaction
from fintrackr.utils import CONFIG_PATH

not_money = r"^\d+$"

class ColMatch(NamedTuple):
    col_header: str
    col_type: str

logger = logging.getLogger(__name__)

def read_rows(path: str)->list[list[str]]:
    # TODO see nice to haves in review - add encoding and so forth
    with open(path, mode='r') as f:
        # Strip spaces around entries on load (particularly important if there's a header row)
        return [[cell.strip() for cell in row] for row in csv.reader(f)]

def get_trans_header_aliases(config_path: str=CONFIG_PATH)->dict:
    trans_aliases = {}
            
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
        # get allowed header aliases
        for t in TRANS_COL_NAMES:
            trans_aliases[t] = config["transaction_headers"][t]
    return trans_aliases

def parse_cell_type(datum: str) -> list[ColMatch]:
    # For one cell in one row, return a list of possible header options it might match

    possible_matches = []

    # Special case columns we want to ignore and not try to parse:
    # 1. Some bank's transaction csvs have columns of all *'s
    # 2. Handle empty cells (including from a trailing comma at end of row)
    # 3. Some banks have separate "check number" columns (but also have "check number" in the description)
    if not len(datum)==0 and not (type(datum)==str and datum.strip()=='*') and len(re.findall(not_money, datum))==0:
        for f in fields(Transaction):
            try:
                _ = f.metadata['csv_parser'](datum) # Can we parse this column per Transaction field specifications
                possible_matches.append(ColMatch(col_header=f.name, col_type=f.metadata['sql_type']))
            except:
                pass # If we couldn't convert this column type, try next loop iteration
    return possible_matches

def id_header_cols(first_row: list[str], aliases: dict[str, list[str]]) -> dict[str, int] | None:
    # If possible, we infer header from the first row, based on header aliases provided in the csv
    
    trans_header = {}

    for k in aliases.keys():
        for c in first_row:
            if c in aliases[k]:
                trans_header[k]=c
    if len(trans_header) == len(aliases):
        # we have a header we recognize; convert to a useable form for creating a new file
        return {val: key for key, val in trans_header.items()}
    else:
        return None

def infer_header_cols(data_rows: list[list[str]]) -> dict[str, int]:
    # See if we can infer which columns are which based on file contents and types
    # If anything is ambiguous, we abort - no guessing
    prev_col_equivs = {}
    num_input_cols = len(data_rows[0])
    for r in data_rows:
        col_equivs = {}
        for c in range(0,num_input_cols): # We may have more columns than we need. See if we can pick out the ones we want
            
            possible_matches = parse_cell_type(datum=r[c])

            if len(possible_matches)>1:
                # We should have >1 possible match for some columns 
                # (since everything should at least parse as a string)
                # Pick the other one (there should be only one)
                if len(possible_matches) != 2:
                    msg = "Too many possible matches for this row, can't disambiguate"
                    logger.error(msg)
                    raise ValueError(msg)
                col_equivs[c] = possible_matches[0].col_header if possible_matches[0].col_type != 'text' else possible_matches[1].col_header
            elif len(possible_matches)>0:
                col_equivs[c] = possible_matches[0].col_header
        
        # Abort if we don't have at least as many possible header matches as Transaction fields
        if len(col_equivs)<len(TRANS_COL_NAMES):
            msg = "Could not parse enough cells; header inference failed"
            logger.error(msg)
            raise ValueError(msg)
        
        # Finally, check against previous rows - again we insist they all parse the same. Abort as soon as we fail.
        if len(prev_col_equivs)>0 and prev_col_equivs != col_equivs:
            msg = "Rows parsed differently, header inference failed"
            logger.error(msg)
            raise ValueError(msg)
        else:
            prev_col_equivs=col_equivs
    return {val: key for key, val in col_equivs.items()}

def write_reformatted(path_to_output: str, data_rows: list[list[str]], header_col_dict: dict[str, int]) -> str:
    # Returns the path it wrote to for confirmation of success

    # Create corrected rows to write
    corrected_dict_list = []
    for r in data_rows:
        new_row = {}
        for k in header_col_dict.keys():
            new_row[header_col_dict[k]] = r[k]
        corrected_dict_list.append(new_row)

    with open(path_to_output, 'w', newline='') as newf:
        writer=csv.DictWriter(newf, fieldnames=header_col_dict.keys())
        writer.writeheader()
        for r in corrected_dict_list:
            writer.writerow(r)
    return path_to_output
    

def reformat_csv(path_to_csv: str, config_path: str=CONFIG_PATH)->str:
    # Given a path to a transactions csv, return a new path to
    # a new csv that's guaranteed to have the right format for loading.
    # Writes a new file regardless of whether the original was ok or not.
    # We pass a config_path arg for testing.
    
    # Basic input checking
    check_csv_path(path_to_file=path_to_csv)

    filename = os.path.splitext(os.path.split(path_to_csv)[-1])[0]
    new_csv_path = os.path.join(os.path.split(path_to_csv)[0], filename+"_REFORMAT"+".csv")

    rows = read_rows(path=path_to_csv)
    if len(rows)==0:
        msg = f"No rows read from {path_to_csv}"
        logger.error(msg)
        raise ValueError(msg)
    
    trans_aliases = get_trans_header_aliases(config_path=config_path)
    
    header_dict = id_header_cols(first_row=rows[0], aliases=trans_aliases)
    if header_dict is not None:
        logger.info(f"File {path_to_csv} has a recognizable header")
        return write_reformatted(path_to_output=new_csv_path, data_rows=rows[1:], header_col_dict=header_dict)
    else:
        logger.info(f"No header with correct aliases identified in file {path_to_csv}")
        header_dict = infer_header_cols(data_rows=rows, header={k:k for k in trans_aliases.keys()})
        return write_reformatted(path_to_output=new_csv_path, data_rows=rows, header_col_dict=header_dict)

    