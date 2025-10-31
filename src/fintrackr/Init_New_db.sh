#!/bin/bash

# Initialize FinTrackr db
# Admin should do this once, users never; can also be called by tests
# First arg is db name, second is username who will be set to owner.
# createdb will fail if db already exists
# TODO pass the error out if creation fails

createuser $2 -d
createdb $1 -O $2
psql $1 < src/fintrackr/schema.sql
  