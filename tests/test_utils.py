# test_utils.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest

from dataclasses import fields

from fintrackr.fin_dataclasses import Transaction
from fintrackr.utils import get_trans_header_aliases, wrangle_trans_csv

from utils_for_tests import TEST_CONFIG_PATH

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
        pass
        