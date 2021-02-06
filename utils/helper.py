import os
import yaml
import random
import requests
import logging
from os.path import dirname
from requests.auth import HTTPBasicAuth
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from utils.const import CommonResult


def load_global_params_config(py_root_path=dirname(__file__)):
    logging.basicConfig(level=logging.INFO, format="(%(threadName)-10s : %(message)s")
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
        self.organization = load_global_params_config()['common_var']['org']
        self.project = load_global_params_config()['common_var']['project']

    def _get_deployment_group_agent(self, deployment_group_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets/?api-version=6.0-preview.1"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()

    def _del_deployment_group_agent(self, target_id, deployment_group_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets/{target_id}?api-version=6.0-preview.1"
        response = requests.delete(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("delete agent in deployment group status_code: {}".format(response.status_code))
        assert response.status_code == 200 or response.status_code == 204
        return CommonResult.Success

    def _update_tags_of_deployment_group_agent(self, deployment_group_id, payload):
        """
        payload = [{"tags": ["db",
                             "web",
                             "newTag5248232320667898861"],
                    "id": 82},
                   {"tags": ["db",
                             "newTag5248232320667898861"],
                    "id": 83}]
        """
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets?api-version=6.0-preview.1"
        if not isinstance(payload, list):
            raise TypeError(f"payload type expect list but actual: {type(payload)}")
        response = requests.patch(url, json=payload, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("update agent tags in deployment group status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return CommonResult.Success

    def _get_release_definition(self, release_definition_id: int):
        url = f"https://vsrm.dev.azure.com/{self.organization}/{self.project}/_apis/release/definitions/{release_definition_id}?api-version=6.0"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()

    def _trigger_release(self, release_definition_id: int):
        url = f"https://vsrm.dev.azure.com/{self.organization}/{self.project}/_apis/release/releases?api-version=6.0"
        payload = {"definitionId": release_definition_id}

        response = requests.post(url, json=payload, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return CommonResult.Success


if __name__ == "__main__":
    pass
