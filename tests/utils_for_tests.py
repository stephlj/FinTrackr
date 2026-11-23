import os
import yaml

TEST_CONFIG_PATH = os.path.join(os.path.dirname(__file__),"fixtures","test_config.yml")
TEST_DATA_PATH = os.path.join(os.path.dirname(__file__),"fixtures")

def config_params_for_tests(test_config_path: str = TEST_CONFIG_PATH) -> dict:
    with open(test_config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
        test_db_name = config["db"]["db_name"]
        test_owner = config["db"]["admin_name"]

    return {
        "test_db_name" : test_db_name,
        "test_owner": test_owner,
        "owner_pw": "test_fin_admin_pw",
        "user": "test_fin_user",
        "user_pw" : "pw",
        "config_path" : test_config_path
    }