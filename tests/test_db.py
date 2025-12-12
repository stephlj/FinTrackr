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
    def setUpClass(cls):
        # Make a test db, in the process also tests init_db and add_user.
        # TODO later use mocking instead of a real db
        
        path_to_config = os.path.join(os.getcwd(),"tests","data","test_config.yml")
        with open(path_to_config, "r") as config_file:
            config = yaml.safe_load(config_file)
            cls.test_db_name = config["db"]["db_name"]
            cls.test_owner = config["db"]["admin_name"]

        cls.owner_pw = "test_pw"

        init_db(pw=cls.owner_pw, path_to_config=path_to_config)

        cls.user = "test_user"
        cls.user_pw = "pw"
        add_user(name=cls.user, 
                 pw=cls.user_pw, 
                 admin_pw = cls.owner_pw, 
                 path_to_config=path_to_config
        )

        cls.conn = psycopg.connect(f"dbname={cls.test_db_name} user={cls.user} password={cls.user_pw} host='localhost'")

    @classmethod
    def tearDownClass(cls):
        # close connection and delete testing db
        cls.conn.close()
        exit_code = subprocess.run(["dropdb", cls.test_db_name])
        exit_code2 = subprocess.run(["dropuser",cls.user])
        exit_code3 = subprocess.run(["dropuser",cls.test_owner])

        # We put these at the end to ensure teardown completes even if one of these fails.
        # Note that the @classmethod decorator changes the first arg to the class not
        # an instance of the class, so self.assertEqual fails.
        assert exit_code.returncode==0, "Failed to remove testing db, must now remove manually"
        assert exit_code2.returncode==0, "Failed to remove testing user, must now remove manually"
        assert exit_code3.returncode==0, "Failed to remove testing db owner, must now remove manually"

    def test_execute(self):
         # Test that we can insert into the db using the fin_db.execute()
         # convenience method

         # use self.assertEqual and similar here
         pass


    def test_add_transactions(self):
    #     # Will test add_transactions method TODO
         pass
