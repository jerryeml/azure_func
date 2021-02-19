import os
import yaml
import random
import requests
import logging
from os.path import dirname
from collections import OrderedDict
from requests.auth import HTTPBasicAuth
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from utils.const import CommonResult


def config_root_logger():
    """
    Reference: https://stackoverflow.com/questions/22643337/per-thread-logging-in-python
    """
    log_file = '/perThreadLogging.log'

    formatter = "%(asctime)-15s" \
                "| %(threadName)-11s" \
                "| %(levelname)-5s" \
                "| %(message)s"

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'root_formatter': {
                'format': formatter
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'root_formatter'
            },
            'log_file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'filename': log_file,
                'formatter': 'root_formatter',
            }
        },
        'loggers': {
            '': {
                'handlers': [
                    'console',
                    'log_file',
                ],
                'level': 'DEBUG',
                'propagate': True
            }
        }
    })


def load_global_params_config(py_root_path=dirname(__file__)):
    config_path = os.path.join(py_root_path,
                               "circles_params.yaml")
    with open(config_path) as f:
        global_params = yaml.load(f.read(), Loader=yaml.SafeLoader)

    logging.debug(f"loading global params config: {config_path}")
    return global_params


def modify_yaml_config(sections, key, value, py_root_path=dirname(__file__)):
    config_path = os.path.join(py_root_path,
                               "circles_params.yaml")
    with open(config_path) as f:
        doc = _ordered_yaml_load(f)

    if isinstance(sections, str):
        doc[sections][key] = value
    else:
        tmp = doc
        for i in range(len(sections)):
            tmp = tmp[sections[i]]
        tmp[key] = value
    with open(config_path, 'w') as f:
        _ordered_yaml_dump(doc, f, default_flow_style=False)


def _ordered_yaml_load(stream, Loader=yaml.SafeLoader,
                       object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def _construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping)
    return yaml.load(stream, OrderedLoader)


def _ordered_yaml_dump(data, stream=None, Dumper=yaml.SafeDumper,
                       object_pairs_hook=OrderedDict, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())

    OrderedDumper.add_representer(object_pairs_hook, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


class AzureDevopsAPI(object):
    def __init__(self, username, az_pat):
        self.username = username
        self.az_pat = az_pat
        self.credentials = BasicAuthentication(self.username, self.az_pat)
        self.organization_url = load_global_params_config()['common_var']['url']
        self.organization = load_global_params_config()['common_var']['org']
        self.project = load_global_params_config()['common_var']['project']
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)

    def _get_deployment_group_agent(self, deployment_group_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets/?api-version=6.0-preview.1"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.debug("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()

    def _del_deployment_group_agent(self, target_id, deployment_group_id):
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/distributedtask/deploymentgroups/{deployment_group_id}/targets/{target_id}?api-version=6.0-preview.1"
        response = requests.delete(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.debug("delete agent in deployment group status_code: {}".format(response.status_code))
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
        logging.debug("update agent tags in deployment group status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return CommonResult.Success

    def _get_release_definition(self, release_definition_id: int):
        url = f"https://vsrm.dev.azure.com/{self.organization}/{self.project}/_apis/release/definitions/{release_definition_id}?api-version=6.0"
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.debug("response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return response.json()

    def _trigger_release(self, release_definition_id: int):
        url = f"https://vsrm.dev.azure.com/{self.organization}/{self.project}/_apis/release/releases?api-version=6.0"
        payload = {"definitionId": release_definition_id}

        response = requests.post(url, json=payload, auth=HTTPBasicAuth(self.username, self.az_pat))
        logging.info("trigger release response status_code: {}".format(response.status_code))
        assert response.status_code == 200
        return CommonResult.Success


if __name__ == "__main__":
    pass
