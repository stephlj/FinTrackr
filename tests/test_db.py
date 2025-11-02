#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import psycopg, unittest, subprocess

from fintrackr.init_db import init_db
from fintrackr.add_user import add_user

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Make a test db, in the process also tests init_db and add_user.
        # TODO later use mocking instead of a real db
        
        self.test_db_name = "test"
        self.test_owner = "test_admin"
        self.owner_pw = "test_pw"

        init_db(pw=self.owner_pw, db_name=self.test_db_name, owner=self.test_owner)

        self.user = "test_user"
        self.user_pw = "pw"
        add_user(name=self.user, pw=self.user_pw, admin_pw = self.owner_pw, db_name=self.test_db_name, db_admin=self.test_owner)

        self.conn = psycopg.connect(f"dbname={self.test_db_name} user={self.user} password={self.user_pw} host='localhost'")

    @classmethod
    def tearDownClass(self):
        # close connection and delete testing db
        self.conn.close()
        exit_code = subprocess.run(["dropdb", self.test_db_name])
        assert exit_code.returncode==0, "Failed to remove testing db"

        exit_code2 = subprocess.run(["dropuser",self.user])
        assert exit_code2.returncode==0, "Failed to remove testing user"

        exit_code3 = subprocess.run(["dropuser",self.test_owner])
        assert exit_code3.returncode==0, "Failed to remove testing db owner"

    def test_execute(self):
         # Test that we can insert into the db using the fin_db.execute()
         # convenience method
         pass


    def test_add_transactions(self):
    #     # Will test add_transactions method TODO
         pass
