# test_io.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import os
import pandas as pd

import fintrackr.io as io
from fintrackr.utils import Col_Def
from fintrackr.testing_utils import TEST_DATA_PATH

class TestIO(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # pathx_out is the file that should (or should not) be created as a result of executing the test,
        # not the file with the correct answer (which is pathx_corr)

        cls.path1 = os.path.join(TEST_DATA_PATH, "test_balances.csv")
        cls.cols1 = [Col_Def(col_name="date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
        ]
        cls.path1_out = os.path.join(TEST_DATA_PATH, "test_balances_REFORMAT.csv")
        cls.path1_corr = os.path.join(TEST_DATA_PATH, "test_balances_fixed.csv")

        cls.path1_2 = os.path.join(TEST_DATA_PATH, "test_balances_noheader.csv")
        cls.cols1_2 = [Col_Def(col_name="date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
        ]
        cls.path1_2_out = os.path.join(TEST_DATA_PATH, "test_balances_noheader_REFORMAT.csv")
        # There is no corr for this one, it's already correct

        cls.path2 = os.path.join(TEST_DATA_PATH, "test_csv_header.csv")
        cls.cols2 = [Col_Def(col_name="Date", col_type="date"),
                Col_Def(col_name="description", col_type="text"),
                Col_Def(col_name="amount", col_type="money")
        ]
        cls.path2_out = os.path.join(TEST_DATA_PATH, "test_csv_header_REFORMAT.csv")
        cls.path2_corr = os.path.join(TEST_DATA_PATH, "test_csv_header_fixed.csv")

        cls.path3 = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols.csv")
        cls.cols3 = [Col_Def(col_name="Post Date", col_type="date"),
                Col_Def(col_name="Description", col_type="text"),
                Col_Def(col_name="Amount", col_type="money")
        ]
        cls.path3_out = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols_REFORMAT.csv")
        cls.path3_corr = os.path.join(TEST_DATA_PATH, "test_csv_header_wrongcols_fixed.csv")

        cls.path4 = os.path.join(TEST_DATA_PATH, "test_data_checking.csv")
        cls.cols4 = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]
        cls.path4_out = os.path.join(TEST_DATA_PATH, "test_data_checking_REFORMAT.csv")
        cls.path4_corr = os.path.join(TEST_DATA_PATH, "test_data_checking_fixed.csv")

        cls.path5 = os.path.join(TEST_DATA_PATH, "test_balances_noheader.csv")
        cls.cols5 = [Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="date", col_type="date"),
        ]
        cls.path5_out = os.path.join(TEST_DATA_PATH, "test_balances_REFORMAT.csv")
        cls.path5_corr = os.path.join(TEST_DATA_PATH, "test_balances_fixed.csv")

        cls.path6 = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype.csv")
        cls.cols6 = [Col_Def(col_name="posted_date", col_type="date"),
                Col_Def(col_name="amount", col_type="money"),
                Col_Def(col_name="description", col_type="text")
        ]
        cls.path6_out = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype_REFORMAT.csv")
        cls.path6_corr = os.path.join(TEST_DATA_PATH, "test_csv_wrongtype_fixed.csv")
    
    @classmethod
    def tearDownClass(cls):
        # Make sure testing files are removed even if tests fail
        try:
            os.remove(cls.path1_2_out) # This shouldn't actually be generated
        except:
            pass

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

        try:
            os.remove(cls.path6_out)
        except:
            pass

    def test_col_type(self):
        all_text = pd.Series({0:"Safeway", 
                              1:"Check # 125", 
                              2:"Credit Card Autopay 123456", 
                              3:"Transfer REF # XY*Z-123 on 12/18",
                              4:"Stuff & things Inc."})
        self.assertEqual(io.col_type(all_text), 'text')
        self.assertNotEqual(io.col_type(all_text), 'money')
        self.assertNotEqual(io.col_type(all_text), 'date')
        
        all_money = pd.Series({0:"0.00", 1:"1200.00", 2:"-123.04"})
        self.assertEqual(io.col_type(all_money), 'money')
        self.assertNotEqual(io.col_type(all_money), 'text')
        self.assertNotEqual(io.col_type(all_money), 'date')

        all_money2 = pd.Series({0:0.00, 1:1200.00, 2:-123.04})
        self.assertEqual(io.col_type(all_money2), 'money')
        self.assertNotEqual(io.col_type(all_money2), 'text')
        self.assertNotEqual(io.col_type(all_money2), 'date')

        not_money = pd.Series({0:"0.0", 1:"1200", 2:"-123.04", 3:"-.02"})
        self.assertEqual(io.col_type(not_money),'')
        self.assertNotEqual(io.col_type(not_money),'money')

        # It looks like pandas adds .00 to the second element on construction/load
        money3 = pd.Series({0:0.0, 1:1200, 2:-123.04, 3:-.02})
        self.assertEqual(io.col_type(money3),'money')
        self.assertNotEqual(io.col_type(money3),'')

        all_dates = pd.Series({0:"01/02/2025",1:"10/02/2026"})
        self.assertEqual(io.col_type(all_dates), 'date')
        self.assertNotEqual(io.col_type(all_dates), 'text')
        self.assertNotEqual(io.col_type(all_dates), 'money')
        
        all_null = pd.Series({0:'',1:'',2:'',3:'',4:''})
        self.assertEqual(io.col_type(all_null), '')
        self.assertNotEqual(io.col_type(all_null), 'text')

        some_ints = pd.Series({0:'',1:'123',2:'456',3:'',4:''})
        self.assertEqual(io.col_type(some_ints), '')
        self.assertNotEqual(io.col_type(some_ints),'money')

        all_special = pd.Series({0:'*',1:'*',2:'*',3:'*'})
        self.assertEqual(io.col_type(all_special), '')
        self.assertNotEqual(io.col_type(all_special), 'text')

        some_special = pd.Series({0:'*',1:'',2:'',3:'*'})
        self.assertEqual(io.col_type(some_special), '')
        self.assertNotEqual(io.col_type(some_special), 'text')

        some_text = pd.Series({0:"", 
                              1:"Check # 125", 
                              2:"Credit Card Autopay 123456", 
                              3:"Transfer REF # XY*Z-123 on 12/18",
                              4:"Stuff & things Inc."})
        self.assertEqual(io.col_type(some_text), '')
        self.assertNotEqual(io.col_type(some_text), 'text')
    
    def test_strip_header(self):
        #TODO
        pass
    
    def test_check_csv_format(self):
        
        # Balances with no header (no change needed)
        result1_2 = io.check_csv_format(filepath=self.path1_2, cols = self.cols1_2)
        self.assertEqual(result1_2, '')
        self.assertFalse(os.path.isfile(self.path1_2_out), "New file was created where it should not have been!")
        
        # Balances with header as expected
        result1 = io.check_csv_format(filepath=self.path1, cols = self.cols1)
        self.assertEqual(result1, self.path1_out)
        self.assertTrue(os.path.isfile(self.path1_out), "New file was NOT created where it should not have been!")
        df_test1 = pd.read_csv(result1, header=None)
        df_correct1 = pd.read_csv(self.path1_corr, header=None)
        pd.testing.assert_frame_equal(df_test1, df_correct1, check_dtype=False)
        os.remove(result1)

        # Header needs removing
        result2 = io.check_csv_format(filepath=self.path2, cols = self.cols2)
        self.assertEqual(result2, self.path2_out)
        self.assertTrue(os.path.isfile(self.path2_out), "New file was NOT created where it should have been!")
        df_test2 = pd.read_csv(result2, header=None)
        df_correct2 = pd.read_csv(self.path2_corr, header=None)
        pd.testing.assert_frame_equal(df_test2, df_correct2, check_dtype=False)
        os.remove(result2)

        # Too many columns, and a header
        result3 = io.check_csv_format(filepath=self.path3, cols = self.cols3)
        self.assertEqual(result3, self.path3_out)
        self.assertTrue(self.path3_out, "New file was NOT created where it should have been!")
        df_test3 = pd.read_csv(result3, header=None)
        df_correct3 = pd.read_csv(self.path3_corr, header=None)
        pd.testing.assert_frame_equal(df_test3, df_correct3, check_dtype=False)
        os.remove(result3)

        # Too many columns, no header
        result4 = io.check_csv_format(filepath=self.path4, cols = self.cols4)
        self.assertEqual(result4, self.path4_out)
        self.assertTrue(self.path4_out, "New file was NOT created where it should have been!")
        df_test4 = pd.read_csv(result4, header=None)
        df_correct4 = pd.read_csv(self.path4_corr, header=None)
        pd.testing.assert_frame_equal(df_test4, df_correct4, check_dtype=False)
        os.remove(result4)

        # Everything correct except column order
        result5 = io.check_csv_format(filepath=self.path5, cols = self.cols5)
        self.assertEqual(result5, self.path5_out)
        self.assertTrue(os.path.isfile(self.path5_out), "New file was NOT created where it should have been!")
        df_test5 = pd.read_csv(result5, header=None)
        df_correct5 = pd.read_csv(self.path5_corr, header=None)
        pd.testing.assert_frame_equal(df_test5, df_correct5, check_dtype=False)
        os.remove(result5)

        # Too many columns, no header - additional variant
        result6 = io.check_csv_format(filepath=self.path6, cols = self.cols6)
        self.assertEqual(result6, self.path6_out)
        self.assertTrue(self.path6_out, "New file was NOT created where it should have been!")
        df_test6 = pd.read_csv(result6, header=None)
        df_correct6 = pd.read_csv(self.path6_corr, header=None)
        pd.testing.assert_frame_equal(df_test6, df_correct6, check_dtype=False)
        os.remove(result6)