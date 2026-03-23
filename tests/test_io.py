import unittest
import os
import pandas as pd

from datetime import date

import fintrackr.io as io
from fintrackr.utils import Col_Def
from fintrackr.testing_utils import TEST_DATA_PATH

class TestIO(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # pathx_out is the file that should (or should not) be created as a result of executing the test,
        # not the file with the correct answer (which is pathx_corr)

        cls.path1 = os.path.join(TEST_DATA_PATH, "test_balances.csv")
        cls.path1_out = os.path.join(TEST_DATA_PATH, "test_balances_REFORMAT.csv")
        cls.cols1 = [Col_Def(col_name="date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
        ]

        cls.path2 = os.path.join(TEST_DATA_PATH, "test_csv_header.csv")
        cls.cols2 = [Col_Def(col_name="Date", col_type="date"),
                Col_Def(col_name="description", col_type="text"),
                Col_Def(col_name="amount", col_type="money")
        ]
        cls.path2_out = os.path.join(TEST_DATA_PATH, "test_csv_header_REFORMAT.csv")
        cls.path2_corr = os.path.join(TEST_DATA_PATH, "test_csv_header_fixed.csv")

        cls.path3 = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols.csv")
        cls.cols3 = [Col_Def(col_name="Post Date", col_type="date"),
                Col_Def(col_name="Amount", col_type="money"),
                Col_Def(col_name="Description", col_type="text")
        ]
        cls.path3_out = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv")
        cls.path3_corr = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols_fixed.csv")

        cls.path4 = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype.csv")
        cls.cols4 = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]
        cls.path4_out = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype_REFORMAT.csv")
        cls.path4_corr = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype_fixed.csv")

        cls.path5 = os.path.join(TEST_DATA_PATH, "test_balances.csv")
        cls.path5_out = os.path.join(TEST_DATA_PATH, "test_balances_REFORMAT.csv")
        cls.cols5 = [Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="date", col_type="date"),
        ]
    
    @classmethod
    def tearDownClass(cls):
        # Make sure testing files are removed even if tests fail
        try:
            os.remove(cls.path1_out) # This shouldn't actually be generated
        except:
            pass

        try:
            os.remove(cls.path2_out)
        except:
            pass

        try:
            os.remove(cls.path3_out)
        except:
            pass

        try:
            os.remove(cls.path4_out)
        except:
            pass

        try:
            os.remove(cls.path5_out)
        except:
            pass

    def test_check_csv_format(self):
        
        # Correct format
        result1 = io.check_csv_format(filepath=self.path1, cols = self.cols1)
        self.assertEqual(result1, '')
        self.assertFalse(os.path.isfile(self.path1_out), "New file was created where it should not have been!")

        # Header needs removing
        result2 = io.check_csv_format(filepath=self.path2, cols = self.cols2)
        self.assertEqual(result2, self.path2_out)
        self.assertTrue(os.path.isfile(self.path2_out), "New file was not created where it should not have been!")
        df_test2 = pd.read_csv(result2, header=None)
        df_correct2 = pd.read_csv(self.path2_corr, header=None)
        pd.testing.assert_frame_equal(df_test2, df_correct2, check_dtype=False)
        os.remove(result2)

        # Too many columns, and a header
        # result3 = io.check_csv_format(filepath=self.path3, cols = self.cols3)
        # self.assertEqual(result3, self.path3_out)
        # self.assertTrue(self.path3_out, "New file was not created where it should not have been!")
        # df_test3 = pd.read_csv(result3, header=None)
        # df_correct3 = pd.read_csv(self.path3_corr, header=None)
        # pd.testing.assert_frame_equal(df_test3, df_correct3)
        # os.remove(result3)

        # Too many columns, no header
        # result4 = io.check_csv_format(filepath=self.path4, cols = self.cols4)
        # self.assertEqual(result4, self.path4_out)
        # self.assertTrue(self.path4_out, "New file was not created where it should not have been!")
        # df_test4 = pd.read_csv(result4, header=None)
        # df_correct4 = pd.read_csv(self.path4_corr, header=None)
        # pd.testing.assert_frame_equal(df_test4, df_correct4)
        # os.remove(result4)

        # Everything correct except column order
        result5 = io.check_csv_format(filepath=self.path5, cols = self.cols5)
        self.assertEqual(result5, self.path5_out)
        self.assertTrue(os.path.isfile(self.path5_out), "New file was not created where it should not have been!")
        os.remove(result5)