import jmespath
import datetime
import logging
import azure.functions as func
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from utils.helper import AzureDevopsAPI, load_global_params_config


class MonitorConfig:
    def __init__(self):
        self.kv_name = load_global_params_config()['azure_devops']['key_vault_name']
        self.kv_uri = f"https://{self.kv_name}.vault.azure.net"
        self.creds = DefaultAzureCredential()
        self.key_vault = SecretClient(vault_url=self.kv_uri, credential=self.creds)
        self.user_name = load_global_params_config()['azure_devops']['user_name']
        self.az_pat = self.key_vault.get_secret('az-devops-pat-user')
        self.minimun_available_count = load_global_params_config()['azure_devops']['minimun_available_count']
        self.dg_id_list = load_global_params_config()['azure_devops']['dg_id_list']


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
    config = MonitorConfig()

    az_devops_api = AzureDevopsAPI(config.user_name, config.az_pat.value)
    is_provision_machines(az_devops_api, config.dg_id_list, config.minimun_available_count)


def is_provision_machines(az_devops_api: AzureDevopsAPI, deployment_group_id_list: list, minimun_available_count: int):
    for dg_id in deployment_group_id_list:
        result = az_devops_api._get_deployment_group_agent(dg_id)
        available_agent_count = jmespath.search("length(value[?contains(tags, 'available') == `true`].agent[?status == 'online'].id)", result)
        if available_agent_count < minimun_available_count:
            logging.info(f"available agent count: {available_agent_count} is less than minimun_count:{minimun_available_count}, do provision")
        else:
            logging.warning(f"available agent count: {available_agent_count}, no need provision")
