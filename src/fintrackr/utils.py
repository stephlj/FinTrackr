"""
Small utilities used by multiple modules.

Copyright (c) 2026 Stephanie Johnson
"""

import os
import csv
import yaml
import logging

from datetime import datetime
from dataclasses import fields

from dbcommons.utils import check_csv_path
from fintrackr.fin_dataclasses import TRANS_COL_NAMES, Transaction

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__),"config.yml")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__),"schema.sql")

date_format = "%m/%d/%Y"

logger = logging.getLogger(__name__)

def get_trans_header_aliases()->dict:
    trans_aliases = {}
            
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
        # get allowed header aliases
        for t in TRANS_COL_NAMES:
            trans_aliases[t] = config["transaction_headers"][t]

def wrangle_trans_csv(path_to_csv: str)->str:
    # Given a path to a transactions csv, return a new path to
    # a new csv that's guaranteed to have the right format for loading.
    # Writes a new file regardless of whether the original was ok or not.
    
    # Basic input checking
    check_csv_path(path_to_file=path_to_csv)

    filename = os.path.splitext(os.path.split(path_to_csv)[-1])[0]
    new_csv_path = os.path.join(os.path.split(path_to_csv)[0], filename+"_REFORMAT"+".csv")
    
    trans_aliases = get_trans_header_aliases()
    trans_header = {}

    # Get the first row of the file. We use this to infer the format.
    with open(path_to_csv, mode='r') as f:
        reader = csv.reader(f)
        first_row = next(reader) # returns a list
        first_row = [s.strip() for s in first_row]

    # First question: Is there a header of a format we accept?
    # Look at the first row (the csv module also has a Sniffer class that
    # can try to determine this, but here we write our own version)
    for k in trans_aliases.keys():
        for c in first_row:
            if c in trans_aliases[k]:
                trans_header[k]=c
    if len(trans_header) == len(trans_aliases):
        logger.info(f"File {path_to_csv} has a recognizable header")
        # Switch to a DictReader, since we know we have a header:
        with open(path_to_csv, mode='r') as f:
            dict_reader = csv.DictReader(f)
            new_file_dict_list = [row for row in dict_reader]
        # Convert header into the one we recognize, save a new file:
        # First: flip key-value pairs in trans_header
        trans_header_flipped = {val: key for key, val in trans_header.items()}
        # Then replace elements of first row (header row) with our preferred header:
        # new_first_row = [trans_header_flipped.get(item, item) for item in first_row]
        # Keep only the columns we want, and change their keys:
        corrected_dict_list = []
        for r in new_file_dict_list:
            new_row = {}
            for k in trans_header_flipped.keys():
                new_row[trans_header_flipped[k]] = r[k]
            corrected_dict_list.append(new_row)
        # TODO test with different column orders!
        
    else:
        logger.info(f"No header with correct aliases identified in file {path_to_csv}")
        trans_header = {k:k for k in trans_aliases.keys()} # No header, so we define one
        col_equivs = {}
        for c in range(0,len(first_row)): # We may have more columns than we need. See if we can pick out the ones we want
            for f in fields(Transaction):
                try:
                    result = f.metadata['csv_parser'](first_row[c]) # Can we parse this column per Transaction field specifications
                    #SPECIAL CASE: Some bank's transaction csvs have columns of all *'s. They parse as strings. We don't want those.
                    if type(result)==str and result.strip()=='*':
                        break
                    col_equivs[f.name]=c
                    break # if we succeed, stop trying
                except:
                    pass # If we couldn't convert this column type, try next loop iteration
        if len(col_equivs) != len(trans_header):
            msg = f"Unable to parse format of transaction csv {path_to_csv}"
            logger.error(msg)
            raise ValueError(msg)
        # Pull out just the columns we want
        with open(path_to_csv, mode='r') as f:
            reader = csv.reader(f) # We know there's no header, so no DictReader
            new_file_list = [row for row in reader]
        corrected_dict_list = []
        for r in new_file_list:
            new_row = {}
            for k in trans_header.keys():
                new_row[trans_header[k]] = r[col_equivs[k]]
            corrected_dict_list.append(new_row)

    # Save corrected file
    with open(new_csv_path, 'w') as newf:
        writer=csv.DictWriter(newf, fieldnames=trans_header.keys())
        writer.writeheader()
        for r in corrected_dict_list:
            writer.writerow(r)
    return new_csv_path