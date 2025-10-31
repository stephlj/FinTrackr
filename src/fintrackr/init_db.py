# init_db.py
"""
Initial setup of the database.

Copyright (c) 2025 Stephanie Johnson
"""

import os, subprocess
import logging

logger = logging.getLogger(__name__)

DEFAULT_LOGGING_FORMAT = (
    "%(levelname)s %(asctime)-15s @ %(module)s.%(funcName)s.%(lineno)d - %(msg)s"
)

def init_db(
        db_name: str = "fin_db",
        owner: str = "admin",
    ) -> None:
    """
    One-time setup for initializing the database.
    This will error out if already created.
    """

    path_to_initscript = os.path.join(os.getcwd(),"src","fintrackr","Init_New_db.sh")  
    logger.debug(f"Attempting to run init script at {path_to_initscript}")

    subprocess.run(["chmod", "+x", path_to_initscript])

    exit_code = subprocess.run([path_to_initscript, db_name, owner])
    logger.debug(f"Init script ran with exit code: {exit_code.returncode}, \
                 stdout: {exit_code.stdout}, \
                    stderr: {exit_code.stderr}")

    #TODO capture error(s) from bash script - eg if db already exists so createdb errors
    assert exit_code.returncode == 0, "Failed to execute script to create db"

    logger.info(f"Script to create database named {db_name} executed successfully")


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format=DEFAULT_LOGGING_FORMAT)
    init_db()