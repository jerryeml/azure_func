import time
import jmespath
import datetime
import threading
import logging
import logging.config
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from utils.helper import AzureDevopsAPI, load_global_params_config


class ThreadLogFilter(logging.Filter):
    """
    This filter only show log entries for specified thread name
    """

    def __init__(self, thread_name, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record):
        return record.threadName == self.thread_name


def start_thread_logging():
    """
    Add a log handler to separate file for current thread
    """
    thread_name = threading.Thread.getName(threading.current_thread())
    log_file = '/perThreadLogging-{}.log'.format("test")
    log_handler = logging.FileHandler(log_file)

    log_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)-15s"
        "| %(threadName)-11s"
        "| %(levelname)-5s"
        "| %(message)s")
    log_handler.setFormatter(formatter)

    log_filter = ThreadLogFilter(thread_name)
    log_handler.addFilter(log_filter)

    logger = logging.getLogger()
    logger.addHandler(log_handler)

    return log_handler


def stop_thread_logging(log_handler):
    # Remove thread log handler from root logger
    logging.getLogger().removeHandler(log_handler)

    # Close the thread log handler so that the lock on log file can be released
    log_handler.close()


def config_root_logger():
    """
    Reference: https://stackoverflow.com/questions/22643337/per-thread-logging-in-python
    """
    log_file = '/perThreadLogging.log'

    formatter = "%(asctime)-15s" \
                "| %(threadName)-11s" \
                "| %(levelname)-5s" \
                "| %(message)s"

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'root_formatter': {
                'format': formatter
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'root_formatter'
            }  # ,
            # 'log_file': {
            #     'class': 'logging.FileHandler',
            #     'level': 'INFO',
            #     'filename': log_file,
            #     'formatter': 'root_formatter',
            # }
        },
        'loggers': {
            '': {
                'handlers': [
                    'console'  # ,
                    # 'log_file',
                ],
                'level': 'INFO',
                'propagate': True
            }
        }
    })


class MonitorConfig:
    def __init__(self, circle_name):
        self.circle_name = circle_name
        self.kv_name = load_global_params_config()['circle_var'][circle_name]['key_vault_name']
        self.kv_uri = f"https://{self.kv_name}.vault.azure.net"
        self.creds = DefaultAzureCredential()
        self.key_vault = SecretClient(vault_url=self.kv_uri, credential=self.creds)
        self.is_provision = 0
        self.provision_release_id = load_global_params_config()['circle_var'][circle_name]['provision_release_id']
        self.user_name = load_global_params_config()['circle_var'][circle_name]['user_name']
        self.az_pat = self.key_vault.get_secret('az-devops-pat-user')
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
        config_root_logger()

        logging.info('Info log entry in main thread.')
        logging.debug('Debug log entry in main thread.')

        for each in range(len(self.circle_list)):
            # logging.info(f'Thread ID: {str(threading.get_ident())}, circle: {self.circle_list[int(each)]}')
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
