import os
import yaml
import random
import logging
from os.path import dirname


def load_global_params_config(py_root_path=dirname(__file__)):
    config_path = os.path.join(py_root_path,
                               "global_params.yaml")
    with open(config_path) as f:
        global_params = yaml.load(f.read(), Loader=yaml.SafeLoader)

    logging.info(f"loading global params config: {config_path}")
    return global_params


class AzureDevopsAPI(object):
    def __init__(self, username, az_pat):
        self.username = username
        self.az_pat = az_pat
        self.organization = load_global_params_config()['azure_devops']['org']
        self.project = load_global_params_config()['azure_devops']['project']


def testing():
    return "123"


if __name__ == "__main__":
    pass
