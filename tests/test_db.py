#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import psycopg2, unittest

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setupClass(self):
        # make a test db
        # TODO later use mocking instead of a real db

    @classmethod
    def tearDownClass(self):
        # delete db

    def test_schema_match(self):
        # Check that the schema of the real db matches this test db 
        # we just made from the schema file

    def test_add_transactions(self):
        # Will test add_transactions method TODO
