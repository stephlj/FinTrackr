#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fin_db.py
"""
Class that connects to the database and manages interactions with it
(adding transasctions, etc).

Copyright (c) 2025 Stephanie Johnson
"""

import psycopg

class FinDB:
    def __init__(self, user, name="fin_db"):
        conn = psycopg.connect(f"dbname={name} user={user}")
        cur = conn.cursor()

    def add_transactions(self, transactions):
        # TODO add logging and exception handling
        success = 0

        #TODO function (elsewhere) that munges input file into transactions to use here

        meta_query = "INSERT INTO data_load_metadata (date_added, username, source) VALUES () RETURNING id"
        meta_id = self.cur.execute(meta_query, ("data_load_metadata",))

        trans_query = "INSERT INTO transactions (poasted_date, amount, description, metadatum_id) VALUES ()"
        success = self.cur.execute(trans_query, ("transactions",))