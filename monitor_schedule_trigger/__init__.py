import os
import time
import jmespath
import threading
import logging
import datetime
import azure.functions as func
from dotenv import load_dotenv
from utils.helper import AzureDevopsAPI, load_global_params_config


class MonitorUtil(object):
    def __init__(self, circle_name):
        self.circle_name = circle_name
        self.is_provision = 0
        self.provision_release_id = load_global_params_config()['circle_var'][circle_name]['provision_release_id']
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = os.getenv('AZ_PAT')
        self.minimun_available_count = load_global_params_config()['circle_var'][circle_name]['minimun_available_count']
        self.dg_id_list = load_global_params_config()['circle_var'][circle_name]['dg_id_list']
        self.az_devops_api = AzureDevopsAPI(self.user_name, self.az_pat)

    def is_provision_machines(self):
        for dg_id in self.dg_id_list:
            result = self.az_devops_api._get_deployment_group_agent(dg_id)
            available_agent_count = jmespath.search("length(value[?contains(tags, 'available') == `true`].agent[?status == 'online'].id)", result)
            if available_agent_count < self.minimun_available_count:
                logging.info(f"deployment group: {dg_id}, available agent count: {available_agent_count} is less than minimun_count:{self.minimun_available_count}, do provision")
                self.is_provision += 1
            else:
                logging.info(f"deployment group: {dg_id}, available agent count: {available_agent_count}, no need provision")

        if self.is_provision > 0:
            return True
        else:
            return False

    def trigger_provision_job(self):
        result = self.az_devops_api._trigger_release(self.provision_release_id)
        assert result == 0
        logging.info(f"Trigger provision_release_id:{self.provision_release_id} successfully")
        return True


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'Python timer trigger function ran at {utc_timestamp}')

    load_dotenv()
    circle_list = list(load_global_params_config()['circle_var'].keys())
    logging.info(circle_list)

    for circle in circle_list:
        logging.info(f"Prepare to monitor resource in {circle}")
        monitor_circle = MonitorUtil(circle)

        if monitor_circle.is_provision_machines() is True:
            result = monitor_circle.trigger_provision_job()
            assert result is True

        logging.info("Function complete")
