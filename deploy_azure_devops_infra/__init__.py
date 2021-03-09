import os
import time
import logging
import azure.functions as func
from dotenv import load_dotenv, dotenv_values
from azure.devops.v6_0.task_agent.models import DeploymentGroupCreateParameter
from azure.devops.v6_0.task_agent.models import TaskAgentPool
from azure.devops.exceptions import AzureDevOpsServiceError
from utils.helper import TaskAgent, load_global_params_config, modify_yaml_config


class InfraUtil(object):
    def __init__(self, circle_name):
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = os.getenv('AZ_PAT')
        self.stage_list = load_global_params_config()['circle_var'][circle_name]['stage_list']
        self.task_agent = TaskAgent(self.user_name, self.az_pat)
        self.ap_circle = []
        self.ap_id = {}
        self.dg_circle = []
        self.dg_id = {}

    def generate_circle_deployment_pool_name(self, circle):
        for stage in self.stage_list:
            self.dg_circle.append("DG-" + circle.upper() + "-" + stage)
        logging.info(f"Deployment group name: {self.dg_circle}")

    def generate_circle_agent_pool_name(self, circle):
        for stage in self.stage_list:
            self.ap_circle.append("AP-" + circle.upper() + "-" + stage)
        logging.info(f"Agent pool name: {self.ap_circle}")

    def create_deployment_group(self, circle):
        for dg in self.dg_circle:
            dg_cp = DeploymentGroupCreateParameter(name=dg)

            try:
                r = self.task_agent.task_agent.add_deployment_group(dg_cp, self.task_agent.project)
                logging.info(f"circle: {circle}, dg: {dg}, dg_id: {r.id}")
                # self.dg_id.append(r.id)
                # self.update_dg_id_to_yaml(circle)

            except AzureDevOpsServiceError as e:
                if "already exists" in e.message:
                    logging.warning(f"deployment group: {dg} already exists")

    def create_agent_pool(self, circle):
        for ap in self.ap_circle:
            ap_params = TaskAgentPool(auto_provision=True,
                                      auto_update=True,
                                      name=ap)

            try:
                r = self.task_agent.task_agent.add_agent_pool(ap_params)
                logging.info(f"circle: {circle}, ap: {ap}, ap_id: {r.id}")
                self.ap_id[ap.split("-")[-1]] = r.id
                self.update_ap_id_yaml(circle)

            except AzureDevOpsServiceError as e:
                if "already exists" in e.message:
                    logging.warning(f"agent pool: {ap} already exists")

    def update_dg_id_to_yaml(self, circle):
        modify_yaml_config(['circle_var', circle], "dg_id_list", self.dg_id)
        logging.info("modify yaml config successfully")

    def update_ap_id_yaml(self, circle):
        modify_yaml_config(['circle_var', circle], "ap_id_list", self.ap_id)
        logging.info("modify yaml config successfully")

    def create_library(self):
        pass


def main(req: func.HttpRequest) -> func.HttpResponse:
    load_dotenv()
    circle_list = list(load_global_params_config()['circle_var'].keys())

    try:
        for circle in circle_list:
            infra = InfraUtil(circle)
            infra.generate_circle_agent_pool_name(circle)
            infra.create_agent_pool(circle)

        return func.HttpResponse(f"This HTTP triggered function executed successfully.")

    except Exception as e:
        return func.HttpResponse(f"Meet Error {e}.", status_code=500)

    else:
        pass


if __name__ == "__main__":
    pass
