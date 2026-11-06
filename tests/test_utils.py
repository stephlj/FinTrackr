# test_utils.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import os
import csv

from dataclasses import fields

from fintrackr.fin_dataclasses import Transaction
from fintrackr.utils import get_trans_header_aliases, wrangle_trans_csv

from utils_for_tests import TEST_CONFIG_PATH, TEST_DATA_PATH

def read_csv_rows(path: str)->list[list[str]]:
    with open(path, newline='') as f:
        return list(csv.reader(f))

class TestUtils(unittest.TestCase):

    def test_get_trans_header_aliases(self):
        # Ensure continued correspondance between Transaction dataclass and config file
        # Note: we check both the prod and testing configs!

        correct_transaction_names = [f.name for f in fields(Transaction)]

        header_dict_prod = get_trans_header_aliases() # default is prod
        self.assertEqual(correct_transaction_names,list(header_dict_prod.keys()))

        header_dict_test = get_trans_header_aliases(config_path=TEST_CONFIG_PATH)
        self.assertEqual(correct_transaction_names,list(header_dict_test.keys()))

    def test_wrangle_trans_csv(self):
        
        with self.subTest("Test a simple header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_simple_header.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_simple_header_fixed.csv")
            csv_out = wrangle_trans_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test one accepted header version"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols_fixed.csv")
            csv_out = wrangle_trans_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test a second accepted header version"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols2.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols2_fixed.csv")
            csv_out = wrangle_trans_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test no header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader_fixed.csv")
            csv_out = wrangle_trans_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test no header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader2.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader2_fixed.csv")
            csv_out = wrangle_trans_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

            
        