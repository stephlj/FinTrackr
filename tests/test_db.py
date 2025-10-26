#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# test_db.py
#
# Copyright (c) 2025 Stephanie Johnson

import psycopg, unittest, os, subprocess

class TestDBSetup(unittest.TestCase):
    @classmethod
    def setupClass(self):
        # make a test db
        # TODO later use mocking instead of a real db

        path_to_initscript = os.path.join(os.getcwd(),"src","fintrackr","Init_New_db.sh")
        
        exit_code = subprocess.run([path_to_initscript,"test"], shell=True)
        self.assertNotEqual(exit_code,0, "Failed to create testing db")

        self.conn = psycopg.connect("dbname = test user=test_user")

    @classmethod
    def tearDownClass(self):
        # delete testing db
        remove_db = subprocess.run(["dropdb","test"],capture_output=True)
        # TODO Check {remove_db.stdout}, {remove_db.stderr}


    def test_schema_match(self):
        # Check that the schema of the real db matches this test db 
        # we just made from the schema file
        pass

    def test_add_transactions(self):
        # Will test add_transactions method TODO
        pass
