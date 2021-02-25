import os
import json
import yaml
import random
import requests
import subprocess
import jmespath
import logging
from os.path import dirname
from collections import OrderedDict
from requests.auth import HTTPBasicAuth
from azure.devops.connection import Connection
from azure.devops.v6_0.pipelines.models import RunPipelineParameters, Variable
from azure.devops.v6_0.release.models import ReleaseStartMetadata
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


def deploy_command_no_return_result(command=None):
    """
    Use az command to delpoy service and get the result back
    :param command: az command, reference: https://docs.microsoft.com/en-us/cli/azure/reference-index?view=azure-cli-latest
    @return: 0 success; 1 fail
    """

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    process.wait()
    if process.returncode != 0:
        logging.error(f"process return code: {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, command)

    return CommonResult.Success


def deploy_command_return_result(command=None):
    """
    Use az command to delpoy service and get the result back
    :param command: az command, reference: https://docs.microsoft.com/en-us/cli/azure/reference-index?view=azure-cli-latest
    @return: list type of command result
    """

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    return_code = process.communicate(input=None)[0]
    process.wait()
    # logging.debug("Retunr value: %s, type: %s", return_code, type(return_code))  # type str
    if process.returncode != 0:
        logging.error(f"process return code: {process.returncode}, return result: {return_code}")
        raise subprocess.CalledProcessError(process.returncode, command)

    transform_json = json.loads(return_code)
    return transform_json


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


class TaskAgent(object):
    def __init__(self, username, az_pat):
        """
        https://github.com/microsoft/azure-devops-python-api
        """
        self.username = username
        self.az_pat = az_pat
        self.organization_url = load_global_params_config()['common_var']['url']
        self.organization = load_global_params_config()['common_var']['org']
        self.project = load_global_params_config()['common_var']['project']
        self.credentials = BasicAuthentication(self.username, self.az_pat)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)
        self.task_agent = self.connection.clients_v6_0.get_task_agent_client()

    def del_deployment_group_agent(self, target_id, deployment_group_id) -> None:
        self.task_agent.delete_deployment_target(self.project, deployment_group_id, target_id)

    def get_deployment_group_agents(self, deployment_group_id) -> list:
        responses = self.task_agent.get_deployment_targets(project=self.project, deployment_group_id=deployment_group_id)
        return responses

    def update_tags_of_deployment_group_agent(self, deployment_group_id, payload: dict):
        """
        payload = [{"tags": ["db",
                             "web",
                             "newTag5248232320667898861"],
                    "id": 82},
                   {"tags": ["db",
                             "newTag5248232320667898861"],
                    "id": 83}]
        """
        responses = self.task_agent.update_deployment_targets(machines=payload, project=self.project, deployment_group_id=deployment_group_id)
        return responses


class Pipeline(object):
    def __init__(self, username, az_pat):
        """
        https://github.com/microsoft/azure-devops-python-api
        """
        self.username = username
        self.az_pat = az_pat
        self.organization_url = load_global_params_config()['common_var']['url']
        self.organization = load_global_params_config()['common_var']['org']
        self.project = load_global_params_config()['common_var']['project']
        self.credentials = BasicAuthentication(self.username, self.az_pat)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)
        self.pipeline = self.connection.clients_v6_0.get_pipelines_client()

    def get_pipeline(self, pipeline_id) -> dict:
        responses = self.pipeline.get_pipeline(self.project, pipeline_id)
        return responses

    def trigger_pipeline(self, run_parameters, pipeline_id) -> dict:
        responses = self.pipeline.run_pipeline(run_parameters, self.project, pipeline_id)
        return responses


class Release(object):
    def __init__(self, username, az_pat):
        self.username = username
        self.az_pat = az_pat
        self.organization_url = load_global_params_config()['common_var']['url']
        self.organization = load_global_params_config()['common_var']['org']
        self.project = load_global_params_config()['common_var']['project']
        self.credentials = BasicAuthentication(self.username, self.az_pat)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)
        self.release = self.connection.clients_v6_0.get_release_client()


class AzureCLI(object):
    def __init__(self, sp_client_id, sp_pwd, tenant_id):
        self.sp_client_id = sp_client_id
        self.sp_pwd = sp_pwd
        self.tenant_id = tenant_id
        self.az_login()

    def az_login(self):
        command = f"az login --service-principal --username {self.sp_client_id} --password {self.sp_pwd} --tenant {self.tenant_id}"
        login_result = deploy_command_return_result(command=command)
        logging.info(f"login_result: {login_result}")
        assert type(login_result) == list
        logging.info("az_login successfully")

    def list_vm_in_dtl(self, lab_name, rg_name, query_jmespath="[]"):
        command = f'az lab vm list --lab-name {lab_name} --resource-group {rg_name} --all --query "{query_jmespath}" --verbose'
        list_result = deploy_command_return_result(command=command)
        return list_result


if __name__ == "__main__":
    az_devops_api = Pipeline("jerry_he@trendmicro.com", "fuq7u2aphiyh75bkxzf4f6bivltayima476jhna4asuyrdenvxua")

    run_params = {
        'variables': {
            'app_name':
                {
                    'isSecret': False,
                    'value': 'hahahello'
                }
        }
    }

    responses = az_devops_api.trigger_pipeline(run_parameters=run_params, pipeline_id=21)
    print(responses)
    # responses = az_devops_api.get_pipeline(21)
    # print(responses.configuration)
    # for each in responses:
    #     if "available" in each.tags and "offline" in each.agent.status:
    #         print(each.id)
