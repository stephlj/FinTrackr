#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import psycopg, unittest, subprocess

from fintrackr.init_db import init_db

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Make a test db, in the process also tests init_db.
        # TODO later use mocking instead of a real db
        
        init_db(db_name="test")

        #self.conn = psycopg.connect("dbname=test user=test_user")
        self.conn = psycopg.connect("dbname=test")

    @classmethod
    def tearDownClass(self):
        # close connection and delete testing db
        self.conn.close()
        exit_code = subprocess.run(["dropdb","test"])
        assert exit_code.returncode==0, "Failed to remove testing db"

    def test_schema_match(self):
        # Check that the schema of the real db matches this test db 
        # we just made from the schema file
        pass

    # def test_add_transactions(self):
    #     # Will test add_transactions method TODO
    #     pass