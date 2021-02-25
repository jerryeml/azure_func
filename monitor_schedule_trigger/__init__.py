import os
import time
import jmespath
import threading
import logging
import datetime
import azure.functions as func
from dotenv import load_dotenv, dotenv_values
from subprocess import CalledProcessError
from utils.helper import AzureDevopsAPI, AzureCLI, load_global_params_config


class MonitorUtil(object):
    def __init__(self, circle_name):
        self.circle_name = circle_name
        self.is_provision = 0
        self.provision_release_id = load_global_params_config()['circle_var'][circle_name]['provision_release_id']
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = os.getenv('AZ_PAT')
        self.sp_client_id = os.getenv('SP_CLIENT_ID')
        self.sp_pwd = os.getenv('SP_PWD')
        self.tenant_id = os.getenv('TENANT_ID')
        self.rg_dtl_name = load_global_params_config()['circle_var'][circle_name]['rg_dtl_name']
        self.minimun_available_count = load_global_params_config()['circle_var'][circle_name]['minimun_available_count']
        self.stage_list = load_global_params_config()['circle_var'][circle_name]['stage_list']
        self.az_devops_api = AzureDevopsAPI(self.user_name, self.az_pat)
        self.az_cli = AzureCLI(self.sp_client_id, self.sp_pwd, self.tenant_id)

    def is_provision_machines(self):
        self.monitor_vm_in_dtl()

        if self.is_provision > 0:
            return True
        else:
            return False

    def monitor_vm_in_dtl(self):
        for stage in self.stage_list:
            try:
                dtl_name = "dtl-" + self.circle_name.lower() + "-" + stage.lower()
                result = self.az_cli.list_vm_in_dtl(dtl_name, self.rg_dtl_name)
                available_vm_count = jmespath.search("length([?tags.status=='available'])", result)

                if available_vm_count < self.minimun_available_count:
                    logging.info(f"Circle: {self.circle_name}, dtl name: {dtl_name}, available agent count: {available_vm_count} is less than minimun_count:{self.minimun_available_count}, do provision")
                    self.is_provision += 1
                else:
                    logging.info(f"Circle: {self.circle_name}, dtl name: {dtl_name}, available agent count: {available_vm_count}, no need provision")
            except CalledProcessError as e:
                if e.returncode == 3:
                    logging.warning(e)
                else:
                    raise

    def monitor_az_agent_in_dg(self):
        """
        This func currently deprecated
        """
        self.dg_id_list = load_global_params_config()['circle_var'][self.circle_name]['dg_id_list']

        for dg_id in self.dg_id_list:
            result = self.az_devops_api._get_deployment_group_agent(dg_id)

            available_agent_count = 0
            for each in result:
                if "available" in each.tags and "online" in each.agent.status:
                    available_agent_count += 1

            if available_agent_count < self.minimun_available_count:
                logging.info(f"Circle: {self.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count} is less than minimun_count:{self.minimun_available_count}, do provision")
                self.is_provision += 1
            else:
                logging.info(f"Circle: {self.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count}, no need provision")

    def trigger_provision_job(self):
        pass


def main(mytimer: func.TimerRequest) -> None:
    load_dotenv()
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    circle_list = list(load_global_params_config()['circle_var'].keys())
    logging.info(f'Python timer trigger function ran at {utc_timestamp}, circle: {circle_list}')

    for circle in circle_list:
        logging.info(f"Prepare to monitor resource in {circle}")
        monitor_circle = MonitorUtil(circle)

        if monitor_circle.is_provision_machines() is True:
            pass
            # result = monitor_circle.trigger_provision_job()
            # assert result is True

        logging.info(f"Circle: {circle}, Function complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()
    circle_list = list(load_global_params_config()['circle_var'].keys())
    for circle in circle_list:
        logging.info(f"Prepare to monitor resource in {circle}")
        monitor_circle = MonitorUtil(circle)
        print(monitor_circle.trigger_provision_job())
