# add_user.py
#
# Copyright (c) 2025 Stephanie Johnson

import os, sys
import logging
import psycopg
import yaml

logger = logging.getLogger(__name__)

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

def add_user(
        name: str,
        pw: str,
        admin_pw: str,
        path_to_config: str
) -> None:
    """Add a new user.

    Parameters
    ----------
    name :  str
        User name to add. Usernames will be associated with any data they add to the db.
    pw : str
        Password for new user.
    admin_pw : str 
        The password for the db owner, set when init_db was run.
    path_to_config : str
        Path to the config file to use, to get db_name, db_admin.

    Returns
    -------
    None

    TODO later: add separate dev role if users can't write to all tables
    """

    with open(path_to_config, "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        db_admin = config["db"]["admin_name"]

    # Connect to the db as admin who has permissions to create role
    conn = psycopg.connect(f"dbname={db_name} user={db_admin} password={admin_pw} host='localhost'")
    conn.autocommit = True
    cur = conn.cursor()
    
    # TODO add to an existing user role
    cur.execute(f"CREATE ROLE {name} WITH LOGIN PASSWORD '{pw}' NOCREATEDB NOCREATEROLE")
    cur.execute(f"GRANT CONNECT ON DATABASE {db_name} TO {name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {name}") # So users can create staging tables
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO {name}")
    # Changed to using cur.copy_expert, so this line shouldn't be necessary anymore:
    # cur.execute(f"GRANT pg_read_server_files TO {name}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
    if len(sys.argv) != 4:
        raise TypeError("add_user.py accepts exactly 3 args")
    path_to_config = os.path.join(os.getcwd(), "src", "fintrackr", "config.yml")
    add_user(name=sys.argv[1], pw=sys.argv[2], admin_pw=sys.argv[3],path_to_config=path_to_config)