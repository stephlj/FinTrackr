import unittest
import os

from datetime import date

import fintrackr.io as io
from fintrackr.utils import Col_Def
from fintrackr.testing_utils import TEST_DATA_PATH

class TestPlotAccntBalances(unittest.TestCase):

    def test_check_csv_format(self):
        
        # Correct format
        path1 = os.path.join(TEST_DATA_PATH, "test_balances.csv")
        cols1 = [Col_Def(col_name="date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
        ]
        result1 = io.check_csv_format(filepath=path1, cols = cols1)
        self.assertEqual(result1, '')

        # Header needs removing
        # TODO do more than check it doesn't error
        path2 = os.path.join(TEST_DATA_PATH, "test_data_cc_header.csv")
        cols2 = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]
        result2 = io.check_csv_format(filepath=path2, cols = cols2)
        self.assertNotEqual(result2, '')

        os.remove(result2)

        # Too many columns

        # Columns not right type