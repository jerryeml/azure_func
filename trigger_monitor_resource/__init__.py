import os
import datetime
import logging
import jmespath
import azure.functions as func
from collections import defaultdict
from subprocess import CalledProcessError
from dotenv import load_dotenv, dotenv_values
from utils.helper import TaskAgent, Pipeline, AzureUtil, load_global_params_config


class MonitorUtil(object):
    def __init__(self, circle_name):
        self.circle_name = circle_name
        self.subscription_id = load_global_params_config()['common_var']['subscription_id']
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = os.getenv('AZ_PAT')
        self.sp_client_id = os.getenv('SP_CLIENT_ID')
        self.sp_pwd = os.getenv('SP_PWD')
        self.tenant_id = os.getenv('TENANT_ID')
        self.rg_dtl_name = load_global_params_config()['circle_var'][circle_name]['rg_dtl_name']
        self.os_type_list = load_global_params_config()['circle_var'][circle_name]['os_type']
        self.minimun_available_count = load_global_params_config()['circle_var'][circle_name]['minimun_available_count'] * len(self.os_type_list)
        self.stage_list = load_global_params_config()['circle_var'][circle_name]['stage_list']
        self.circe_status = []
        self.circe_env_status = {"circle": "", "env": "", "agent pool": "",
                                 "agent": "", "available count": "", "minimun count": "", "provision": ""}

    def monitor_vm_in_dtl(self):
        """
        """
        az = AzureUtil(self.sp_client_id, self.sp_pwd, self.tenant_id, self.subscription_id)
        for stage in self.stage_list:
            try:
                dtl_name = "dtl-" + self.circle_name.lower() + "-" + stage.lower()
                logging.info(f"monitoring: {dtl_name}....")

                result = az.list_vm_in_dtl(dtl_name, self.rg_dtl_name)
                available_vm_count = 0
                for each in result:
                    if "available" in each.tags['status']:
                        available_vm_count += 1

                if available_vm_count < self.minimun_available_count:
                    logging.info(f"Circle: {self.circle_name}, dtl name: {dtl_name}, available agent count: {available_vm_count} is less than minimun_count:{self.minimun_available_count}, do provision")
                    self.trigger_provision_job(stage)
                else:
                    logging.info(f"Circle: {self.circle_name}, dtl name: {dtl_name}, available agent count: {available_vm_count}, no need provision")

            except CalledProcessError as e:
                if e.returncode == 3:
                    logging.warning(e)
                else:
                    raise

    def monitor_az_agent_in_dg(self):
        """
        """
        self.task_agent = TaskAgent(self.user_name, self.az_pat)
        self.dg_id_list = load_global_params_config()['circle_var'][self.circle_name]['dg_id_list']

        for dg_id in self.dg_id_list:
            result = self.task_agent.get_deployment_group_agents(dg_id)

            available_agent_count = 0
            for each in result:
                if "available" in each.tags and "online" in each.agent.status:
                    available_agent_count += 1

            if available_agent_count <= self.minimun_available_count:
                logging.info(f"Circle: {self.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count} is less than minimun_count:{self.minimun_available_count}, do provision")
            else:
                logging.info(f"Circle: {self.circle_name}, deployment group: {dg_id}, available agent count: {available_agent_count}, no need provision")

    def monitor_az_agent_in_ag(self):
        """
        """
        self.task_agent = TaskAgent(self.user_name, self.az_pat)
        self.ap_id_list = load_global_params_config()['circle_var'][self.circle_name]['ap_id_list']

        for env, ap_id in self.ap_id_list.items():
            result = self.task_agent.get_agent_pool_agents(ap_id)
            logging.info(f"Get {env} agents in agent pool: {ap_id} return: {result}")
            available_agent_count = 0
            for each in result:
                logging.debug(f"Circle: {self.circle_name}, env: {env}, agent pool: {ap_id}, agent: {each}")
                if "online" in each.status:
                    available_agent_count += 1
    
            if available_agent_count <= self.minimun_available_count:
                logging.info(f"available agent count: {available_agent_count} less than minimun_count:{self.minimun_available_count}, do provision")
                provision = True
                # self.trigger_provision_job(env)
            else:
                logging.info(f"available agent count: {available_agent_count}, no need provision")
                provision = False
            
            self.circe_env_status = {"circle": self.circle_name, "env": env, "agent pool": ap_id,
                                     "agent": each, "available count": available_agent_count, "minimun count": self.minimun_available_count, "provision": provision}
            self.circe_status.append(self.circe_env_status)


    def trigger_provision_job(self, stage):
        """
        trigger provision vm in specific dev test lab
        """
        provision_pipeline_id = load_global_params_config()['circle_var'][self.circle_name]['provision_pipeline_id']
        pipeline = Pipeline(self.user_name, self.az_pat)

        run_params = {
            'variables': {
                'app_name':
                {
                    'isSecret': False,
                    'value': self.circle_name
                },
                'vm_count':
                {
                    'isSecret': False,
                    'value': self.minimun_available_count // len(self.os_type_list)
                },
                'env':
                {
                    'isSecret': False,
                    'value': stage
                }
            }
        }

        pipeline.trigger_pipeline(run_params, provision_pipeline_id)


def main(req: func.HttpRequest) -> func.HttpResponse:
    load_dotenv()
    circle_list = list(load_global_params_config()['circle_var'].keys())
    api_response = []
    logging.info(f'Python HTTP trigger function processed a request. circle: {circle_list}')

    try:
        for circle in circle_list:
            logging.info(f"Prepare to monitor resource in {circle}")
            monitor_circle = MonitorUtil(circle)
            monitor_circle.monitor_az_agent_in_ag()

            logging.info(f"Circle: {circle}, Function complete: {monitor_circle.circe_status}")
            api_response.append(monitor_circle.circe_status)
        return func.HttpResponse(f"This HTTP triggered function executed successfully. {api_response}")

    except Exception as e:
        return func.HttpResponse(f"Meet Error {e}.", status_code=500)


if __name__ == "__main__":
    pass
