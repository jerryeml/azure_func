import logging
import azure.functions as func
from utils.helper import AzureDevopsAPI


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request. First time to use azure functions')
    name = req.params.get('name')
    pat = req.params.get('pat')
    az_devops_api = AzureDevopsAPI(name, pat)

    if name and pat:
        logging.info(f"testing:{az_devops_api}")
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse("This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                                 status_code=404)
