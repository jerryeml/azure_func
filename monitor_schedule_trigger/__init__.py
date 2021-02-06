import logging
import datetime
import azure.functions as func
from utils.runner import MonitorConfig, MutiRunner
from utils.helper import AzureDevopsAPI, load_global_params_config


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
    circle_list = list(load_global_params_config()['circle_var'].keys())
    logging.info(circle_list)

    d = MutiRunner(circle_list)
    d.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="(%(threadName)-10s : %(message)s")
    circle_list = list(load_global_params_config()['circle_var'].keys())
    d = MutiRunner(circle_list)
    d.run()
