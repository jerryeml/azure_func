import time
import logging
import datetime
import azure.functions as func
from dotenv import load_dotenv, dotenv_values


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'Python timer trigger function ran at {utc_timestamp}')


if __name__ == "__main__":
    pass
