# test_reformat_inputs.py
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
import os
import csv

from dataclasses import fields

from fintrackr.fin_dataclasses import Transaction
from fintrackr.reformat_inputs import get_trans_header_aliases, parse_cell_type, id_header_cols, disambiguate_col, infer_header_cols, reformat_csv, ColMatch

from utils_for_tests import TEST_CONFIG_PATH, TEST_DATA_PATH

def read_csv_rows(path: str)->list[list[str]]:
    with open(path, newline='') as f:
        return list(csv.reader(f))

class TestReformatInputs(unittest.TestCase):

    def test_get_trans_header_aliases(self):
        # Ensure continued correspondance between Transaction dataclass and config file
        # Note: we check both the prod and testing configs!

        correct_transaction_names = [f.name for f in fields(Transaction)]

        header_dict_prod = get_trans_header_aliases() # default is prod
        self.assertEqual(correct_transaction_names,list(header_dict_prod.keys()))

        header_dict_test = get_trans_header_aliases(config_path=TEST_CONFIG_PATH)
        self.assertEqual(correct_transaction_names,list(header_dict_test.keys()))

    def test_parse_cell_type(self):
        with self.subTest("Test a date"):
            self.assertEqual([ColMatch(col_header='posted_date',col_type='date'),
                                       ColMatch(col_header='description',col_type='text')],
                             parse_cell_type(datum='09/02/2026'))

        with self.subTest("Test an amount"):
            self.assertEqual([ColMatch(col_header='amount',col_type='numeric(12,2)'),
                                        ColMatch(col_header='description',col_type='text')],
                                parse_cell_type(datum='200.00'))

        with self.subTest("Test a negative amount"):
            self.assertEqual([ColMatch(col_header='amount',col_type='numeric(12,2)'),
                                        ColMatch(col_header='description',col_type='text')],
                                parse_cell_type(datum='-43.12'))

        with self.subTest("Test we do NOT catch non-money and non-integer amounts"):
            # This test logs unideal but expected behavior
            self.assertEqual([ColMatch(col_header='amount',col_type='numeric(12,2)'),
                                       ColMatch(col_header='description',col_type='text')],
                            parse_cell_type(datum='-43.1'))

        with self.subTest("Test unambiguous text"):
            self.assertEqual([ColMatch(col_header='description',col_type='text')],
                                parse_cell_type(datum='A description'))

        with self.subTest("Test ambiguity between numbers and text"):
            self.assertEqual([], parse_cell_type(datum='200'))

        with self.subTest("Test special column types - asterisks"):
            self.assertEqual([], parse_cell_type(datum='*'))

        with self.subTest("Test special column types - empty"):
            self.assertEqual([], parse_cell_type(datum=''))

        with self.subTest("Test text with special characters"):
            self.assertEqual([ColMatch(col_header='description',col_type='text')], parse_cell_type(datum='123 gas station'))

        with self.subTest("Test text with special characters"):
            self.assertEqual([ColMatch(col_header='description',col_type='text')], parse_cell_type(datum='*Safeway'))

        with self.subTest("Test text with special characters"):
            self.assertEqual([ColMatch(col_header='description',col_type='text')], parse_cell_type(datum='Check # 100'))
    
    def test_id_header_cols(self):
        aliases = {'posted_date': ["Post Date", "DATE"], 
                   'amount': ["Amount", "AMOUNT"], 
                   'description': ["Description","DESCRIPTION"]}

        with self.subTest('Input with simple header'):
            first_row = ['DATE','DESCRIPTION','AMOUNT']
            self.assertEqual({'posted_date':0,'amount':2,'description':1},
                                id_header_cols(first_row=first_row,aliases=aliases))
        
        with self.subTest('Input with header matching extacols_v2'):
            first_row = ['DATE','DESCRIPTION','AMOUNT','CHECK #', 'STATUS']
            self.assertEqual({'posted_date':0,'amount':2,'description':1},
                             id_header_cols(first_row=first_row,aliases=aliases))

        with self.subTest('Input with header matching extacols'):
            first_row = ['Transaction Date','Post Date','Description','Category', 'Type', 'Amount', 'Memo']
            self.assertEqual({'posted_date':1,'amount':5,'description':2},
                             id_header_cols(first_row=first_row,aliases=aliases))

        with self.subTest('Input with header matching wrongheader.csv'):
            first_row = ['DATE','WRONGTHING','AMOUNT','CHECK#','STATUS']
            self.assertIsNone(id_header_cols(first_row=first_row,aliases=aliases))

        with self.subTest('Input with no header'):
            first_row = ['09/10/2025','26.57','*','','Safeway']
            self.assertIsNone(id_header_cols(first_row=first_row,aliases=aliases))

    def test_disambiguate_col(self):
        # Almost everything should parse as text - 
        # we're disambiguating text from something that could also be a date or numeric

        with self.subTest("Test a date"):
            possible_matches = [ColMatch(col_header='posted_date',col_type='date'),
                                ColMatch(col_header='description',col_type='text')]
            self.assertEqual('posted_date', disambiguate_col(possible_matches))
        
        with self.subTest("Test an amount"):
            possible_matches=[ColMatch(col_header='amount',col_type='numeric(12,2)'),
                                ColMatch(col_header='description',col_type='text')]
            self.assertEqual('amount',disambiguate_col(possible_matches))

        with self.subTest("Test unambiguous text"):
            possible_matches=[ColMatch(col_header='description',col_type='text')]
            self.assertEqual('description',disambiguate_col(possible_matches))

        with self.subTest("Test too many possible matches"):
            # I don't think this could actually happen
            possible_matches=[ColMatch(col_header='posted_date',col_type='date'),
                              ColMatch(col_header='amount',col_type='numeric(12,2)'),
                              ColMatch(col_header='description',col_type='text')]
            with self.assertRaises(ValueError):
                _ = disambiguate_col(possible_matches)

        with self.subTest("Test duplicate matches"):
            # I don't think this could actually happen
            possible_matches=[ColMatch(col_header='description',col_type='text'),
                                ColMatch(col_header='description',col_type='text')]
            with self.assertRaises(ValueError):
                _ = disambiguate_col(possible_matches)

        # Calling function has an if to catch empty lists so we don't test that here
    
    def test_infer_header_cols(self):
        with self.subTest("Test no_header file contents"):
            data_rows = read_csv_rows(os.path.join(TEST_DATA_PATH,"test_csv_noheader.csv"))
            self.assertEqual({'posted_date':0,'amount':1, 'description':4}, infer_header_cols(data_rows=data_rows))

        with self.subTest("Test no_header2 file contents"):
            data_rows = read_csv_rows(os.path.join(TEST_DATA_PATH,"test_csv_noheader2.csv"))
            self.assertEqual({'posted_date':0,'amount':1, 'description':4}, infer_header_cols(data_rows=data_rows))

        with self.subTest("Test no_header3 file contents"):
            data_rows = read_csv_rows(os.path.join(TEST_DATA_PATH,"test_csv_noheader3.csv"))
            self.assertEqual({'posted_date':0,'amount':1, 'description':4}, infer_header_cols(data_rows=data_rows))

        with self.subTest("Test no_header4 file contents"):
            data_rows = read_csv_rows(os.path.join(TEST_DATA_PATH,"test_csv_noheader4.csv"))
            self.assertEqual({'posted_date':0,'amount':1, 'description':4}, infer_header_cols(data_rows=data_rows))

        with self.subTest("Test noheader_wrongcontent"):
            data_rows = read_csv_rows(os.path.join(TEST_DATA_PATH,"test_csv_noheader_wrongcontent.csv"))
            with self.assertRaises(ValueError):
                _ = infer_header_cols(data_rows=data_rows)

    
    def test_reformat_csv(self):
        
        with self.subTest("Test a simple header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_simple_header.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_simple_header_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test one accepted header version"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test a second accepted header version"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols2.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols2_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test a second accepted header version with extraneous spaces"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols_spaces.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_header_extracols_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test no header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        with self.subTest("Test a second version of no header"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader2.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader2_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))

        # Test cases covering bugs caught by Claude during code review:
        with self.subTest("Test no header starting with two check rows"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader3.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader3_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))
        with self.subTest("Test no header with a trailing empty column"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader4.csv")
            csv_fixed = os.path.join(TEST_DATA_PATH, "test_csv_noheader4_fixed.csv")
            csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
            self.addCleanup(os.remove, csv_out)
            self.assertEqual(read_csv_rows(csv_out), read_csv_rows(csv_fixed))
        with self.subTest("Test we abort on an empty file"):
            csv_in = os.path.join(TEST_DATA_PATH, "blank.csv")
            with self.assertRaises(ValueError):
                csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
                self.addCleanup(os.remove, csv_out)
        with self.subTest("Test we abort if not all rows parse the same"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader_differentrow_parse.csv")
            with self.assertRaises(ValueError):
                csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
                self.addCleanup(os.remove, csv_out)


        with self.subTest("Test a header with columns that don't match config"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_wrongheader.csv")
            with self.assertRaises(ValueError):
                csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
                self.addCleanup(os.remove, csv_out)

        with self.subTest("Test no header, column contents that don't match expected"):
            csv_in = os.path.join(TEST_DATA_PATH, "test_csv_noheader_wrongcontent.csv")
            with self.assertRaises(ValueError):
                csv_out = reformat_csv(path_to_csv=csv_in, config_path=TEST_CONFIG_PATH)
                self.addCleanup(os.remove, csv_out)

            
        