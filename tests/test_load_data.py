# test_load_data.py - unit tests
#
# Copyright (c) 2026 Stephanie Johnson

import unittest
from unittest.mock import Mock

import fintrackr.load_data

class TestLoadData(unittest.TestCase):
    # @classmethod
    # def setUpClass(cls):
    #     def add_rows_side_effect(f, acct):
    #         if f == "path_to_new_rows" and acct == "new":
    #             return 1
    #         elif f == "path_to_new_rows" and acct == "existing":
    #             return 0
    #         else:
    #             return 0

    #     mock_db_conn = Mock(side_effect=add_rows_side_effect)
    #     mock_db_conn.csv_to_staging.return_value = 1
    #     mock_db_conn.add_balances_from_staging.return_value = 1
    #     mock_db_conn.execute_action.response = "DROP TABLE"

    def test_add_balances(self):
        pass