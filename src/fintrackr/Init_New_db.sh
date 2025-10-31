#!/bin/bash

# Initialize FinTrackr db
# Admin should do this once, users never; can also be called by tests
# First arg is db name, second is username who will be set to owner,
# third arg is pw for owner.
# createdb will fail if db already exists
# TODO pass the error out if creation fails

psql -d postgres -c "CREATE ROLE $2 WITH LOGIN PASSWORD '$3' CREATEDB CREATEROLE;"
createdb $1 -O $2
psql -d postgres -c "REVOKE CONNECT ON DATABASE $1 FROM PUBLIC;"
psql -d postgres -c "GRANT CONNECT ON DATABASE $1 TO $2;"
psql $1 < src/fintrackr/schema.sql
  