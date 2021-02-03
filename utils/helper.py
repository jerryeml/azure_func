import os
import yaml
import random
import requests
import logging
from os.path import dirname
from requests.auth import HTTPBasicAuth
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


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
        self.credentials = BasicAuthentication(self.username, self.az_pat)
        self.organization = load_global_params_config()['azure_devops']['org']
        self.project = load_global_params_config()['azure_devops']['project']

    def _get_deployment_group_agent(self, deployment_group_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets/?api-version=6.0-preview.1"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()

    def _get_release_definition(self, release_definition_id):
        url = f"https://vsrm.dev.azure.com/{self.organization}/{self.project}/_apis/release/definitions/{release_definition_id}?api-version=6.0"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        print("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()


if __name__ == "__main__":
    pass
