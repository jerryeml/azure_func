import os
import time
import jmespath
import datetime
import threading
import logging
from utils.helper import AzureDevopsAPI, load_global_params_config


class MonitorConfig:
    def __init__(self, circle_name):
        self.circle_name = circle_name
        self.is_provision = 0
        self.provision_release_id = load_global_params_config()['circle_var'][circle_name]['provision_release_id']
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = os.getenv('AZ_PAT')
        self.minimun_available_count = load_global_params_config()['circle_var'][circle_name]['minimun_available_count']
        self.dg_id_list = load_global_params_config()['circle_var'][circle_name]['dg_id_list']


class MutiRunner:
    def __init__(self, circle_list: list):
        self.t_list = []
        self.circle_list = circle_list

    def do_something(self, i):
        logging.info(f'No.{str(i)} Thread ID: {str(threading.get_ident())}, circle: {self.circle_list[int(i)]}')
        self.config = MonitorConfig(self.circle_list[int(i)])
        az_devops_api = AzureDevopsAPI(self.config.user_name, self.config.az_pat.value)

        self.is_provision_machines(az_devops_api, self.config.dg_id_list, self.config.minimun_available_count)
        if self.config.is_provision > 0:
            self.trigger_provision_job(az_devops_api, self.config.provision_release_id)

    def run(self):
        # config_root_logger()

        for each in range(len(self.circle_list)):
            self.t_list.append(threading.Thread(target=self.do_something, args=str(each)))
            time.sleep(1)
            self.t_list[each].start()

        for each in self.t_list:
            each.join()

    def is_provision_machines(self, az_devops_api: AzureDevopsAPI, deployment_group_id_list: list, minimun_available_count: int):
        for dg_id in deployment_group_id_list:
            result = az_devops_api._get_deployment_group_agent(dg_id)
            available_agent_count = jmespath.search("length(value[?contains(tags, 'available') == `true`].agent[?status == 'online'].id)", result)
            if available_agent_count < minimun_available_count:
                logging.info(f"Thread ID: {str(threading.get_ident())}, circle: {self.config.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count} is less than minimun_count:{minimun_available_count}, do provision")
                is_provision += 1
            else:
                logging.info(f"Thread ID: {str(threading.get_ident())}, circle: {self.config.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count}, no need provision")

    def trigger_provision_job(self, az_devops_api: AzureDevopsAPI, provision_pipeline_id: int):
        result = az_devops_api._trigger_release(provision_pipeline_id)
        assert result == 0
