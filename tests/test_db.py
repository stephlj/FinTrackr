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
        
        self.test_db_name = "test"
        self.test_owner = "test_admin"

        init_db(db_name=self.test_db_name,owner=self.test_owner)

        # TODO connect as something other than owner
        # When uncomment this line, also uncomment the one that closes the connection in teardown!
        # self.conn = psycopg.connect(f"dbname={self.test_db_name} user={self.test_owner}")

    @classmethod
    def tearDownClass(self):
        # close connection and delete testing db
        # self.conn.close()
        # TODO drop as the owner not as superuser
        exit_code = subprocess.run(["dropdb", self.test_db_name])
        assert exit_code.returncode==0, "Failed to remove testing db"

        exit_code2 = subprocess.run(["dropuser",self.test_owner])
        assert exit_code2.returncode==0, "Failed to remove testing db owner"

    def test_execute(self):
         # Test that we can insert into the db using the fin_db.execute()
         # convenience method
         pass


    def test_add_transactions(self):
    #     # Will test add_transactions method TODO
         pass
