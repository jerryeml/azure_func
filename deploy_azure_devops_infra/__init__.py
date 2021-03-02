import logging
import time
import azure.functions as func
from azure.devops.v6_0.task_agent.models import DeploymentGroupCreateParameter
from azure.devops.exceptions import AzureDevOpsServiceError
from utils.helper import TaskAgent, load_global_params_config, modify_yaml_config


class InfraUtil(object):
    def __init__(self, user_name, az_pat):
        self.user_name = user_name
        self.az_pat = az_pat
        self.task_agent = TaskAgent(self.user_name, self.az_pat)
        self.circle_list_need_to_deploy = load_global_params_config()['circle_var'].keys()

    def generate_circle_infra_name(self, circle):
        self.dg_circle = ["DG-" + circle.upper() + "-INT",
                          "DG-" + circle.upper() + "-DEV",
                          "DG-" + circle.upper() + "-STG",
                          "DG-" + circle.upper() + "-PROD"]
        self.dg_id = []
        print(f"{self.dg_circle}")

    def create_deployment_group(self, circle):
        for dg in self.dg_circle:
            dg_cp = DeploymentGroupCreateParameter(name=dg)

            try:
                r = self.task_agent.connection.clients_v6_0.get_task_agent_client().add_deployment_group(dg_cp, self.task_agent.project)
                logging.info(f"circle: {circle}, dg: {dg}, dg_id: {r.id}")
                self.dg_id.append(r.id)
                self.update_dg_id_to_yaml(circle)

            except AzureDevOpsServiceError as e:
                if "already exists" in e.message:
                    logging.warning(f"deployment group: {dg} already exists")

    def update_dg_id_to_yaml(self, circle):
        modify_yaml_config(['circle_var', circle], "dg_id_list", self.dg_id)
        logging.info("modify yaml config successfully")

    def create_library(self):
        pass

    def deploy_azure_devops_infra(self):
        """
        1. Deploy circle deployment group
        """
        for circle in self.circle_list_need_to_deploy:
            self.generate_circle_infra_name(circle)
            self.create_deployment_group(circle)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        logging.info("I am not sleep")
        time.sleep(60)
        logging.info("I am wake up")
    except ValueError:
        pass
    else:
        user_name = req_body.get('name')
        az_pat = req_body.get('pat')

    if user_name and az_pat:
        return func.HttpResponse(f"Hello, {user_name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse("This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                                 status_code=200)


if __name__ == "__main__":
    t = InfraUtil("jerry_he@trendmicro.com", "fuq7u2aphiyh75bkxzf4f6bivltayima476jhna4asuyrdenvxua")
    t.deploy_azure_devops_infra()
