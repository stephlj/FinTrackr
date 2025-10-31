#!/bin/bash

# Initialize FinTrackr db
# Admin should do this once, users never; can also be called by tests
# Arg is db name. createdb will fail if db already exists
# TODO pass the error out if creation fails

createdb $1
psql $1 < src/fintrackr/schema.sql
  