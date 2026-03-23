import unittest

import fintrackr.utils as utils

class TestUtils(unittest.TestCase):

    def test_valid_date(self):

        self.assertFalse(utils.valid_date("03/25/24"))

        self.assertTrue(utils.valid_date("03/25/2024"))

        self.assertTrue(utils.valid_date("3/25/2024"))

        self.assertFalse(utils.valid_date("3-25-2024"))

        self.assertFalse(utils.valid_date("2024-03-25"))

    def test_equiv_col_types(self):

        self.assertTrue(utils.equiv_col_types("date", "date"))

        self.assertTrue(utils.equiv_col_types("float", "money"))

        self.assertTrue(utils.equiv_col_types("str", "text"))

        self.assertFalse(utils.equiv_col_types("object", "date"))



