import logging
import azure.functions as func
from test.helper import testing


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request. First time to use azure functions')
    name = req.params.get('name')
    pat = req.params.get('pat')
    r = testing()

    if name and pat:
        logging.info(f"testing:{r}")
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse("This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                                 status_code=404)
