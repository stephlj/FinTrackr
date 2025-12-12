#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import psycopg
import unittest
import subprocess, os
import yaml

from fintrackr.init_db import init_db
from fintrackr.add_user import add_user

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Make a test db, in the process also tests init_db and add_user.
        # TODO later use mocking instead of a real db
        
        path_to_config = os.path.join(os.getcwd(),"tests","data","test_config.yml")
        with open(path_to_config, "r") as config_file:
            config = yaml.safe_load(config_file)
            self.test_db_name = config["db"]["db_name"]
            self.test_owner = config["db"]["admin_name"]

        self.owner_pw = "test_pw"

        init_db(pw=self.owner_pw, path_to_config=path_to_config)

        self.user = "test_user"
        self.user_pw = "pw"
        add_user(name=self.user, 
                 pw=self.user_pw, 
                 admin_pw = self.owner_pw, 
                 path_to_config=path_to_config
        )

        self.conn = psycopg.connect(f"dbname={self.test_db_name} user={self.user} password={self.user_pw} host='localhost'")

    @classmethod
    def tearDownClass(self):
        # close connection and delete testing db
        self.conn.close()
        exit_code = subprocess.run(["dropdb", self.test_db_name])
        exit_code2 = subprocess.run(["dropuser",self.user])
        exit_code3 = subprocess.run(["dropuser",self.test_owner])

        # We put these at the end to ensure teardown completes even if one of these fails
        # self.assertEqual fails here for some reason TODO figure out why
        assert exit_code.returncode==0, "Failed to remove testing db"
        assert exit_code2.returncode==0, "Failed to remove testing user"
        assert exit_code3.returncode==0, "Failed to remove testing db owner"

    def test_execute(self):
         # Test that we can insert into the db using the fin_db.execute()
         # convenience method

         # use self.assertEqual and similar here, even though that isn't working in teardown ... 
         pass


    def test_add_transactions(self):
    #     # Will test add_transactions method TODO
         pass
