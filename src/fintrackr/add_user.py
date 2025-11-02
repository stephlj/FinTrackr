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
        db_name: str,
        db_admin: str,
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
    db_name: str
        Name of database to create user for. This makes testing easier;
        if run from command line, this is inferred from the config file.
    db_admin: str
        Name of admin account (db owner). This makes testing easier;
        if run from the command line, this is inferred from the config file.

    Returns
    -------
    None

    TODO later: add separate dev role if users can't write to all tables
    """

    # Connect to the db as admin who has permissions to create role
    conn = psycopg.connect(f"dbname={db_name} user={db_admin} password={admin_pw} host='localhost'")
    conn.autocommit = True
    cur = conn.cursor()
    
    # TODO add to an existing user role
    cur.execute(f"CREATE ROLE {name} WITH LOGIN PASSWORD '{pw}' NOCREATEDB NOCREATEROLE")
    cur.execute(f"GRANT CONNECT ON DATABASE {db_name} TO {name}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
    if len(sys.argv) != 4:
        raise TypeError("add_user accepts exactly 3 args")
    with open(os.path.join(os.getcwd(), "src", "fintrackr", "config.yml"), "r") as config_file:
        config = yaml.safe_load(config_file)
        db_name = config["db"]["db_name"]
        db_owner = config["db"]["admin_name"]
    add_user(name=sys.argv[1], pw=sys.argv[2], admin_pw=sys.argv[3],db_name=db_name, db_admin=db_owner)