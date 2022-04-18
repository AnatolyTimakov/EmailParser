import sys
import json
import threading
import logging
from Email_reader import email_manager
from logging.handlers import WatchedFileHandler


class EmailDaemon():
    def __init__(self, config_file, logger=None):
        self.config_file = config_file
        self.config = self._load_config(config_file)
        # logging.basicConfig(format=self.config['log_format'])
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger()

        if self.config['log_file']:
            fh = WatchedFileHandler(self.config['log_file'])
            formatter = logging.Formatter(self.config['log_format'])
            fh.setFormatter(formatter)
            self.log.addHandler(fh)

        self.log.setLevel(getattr(logging, self.config['log_level']))
        self.log.info('Loaded config')
        self.log.debug('Config: %s', self.config)

        self.end_event = threading.Event()
        self.reload_event = threading.Event()

        self.email = email_manager(self.log, self.config)

        self.log.info('EmailDaemon inited')

    def _load_config(self, config_file):
        # default log format
        log_format = [
            "[PID: %(process)d]",
            "%(asctime)s",
            "[%(levelname)s]",
            "%(module)s:%(funcName)s:%(lineno)d",
            "%(message)s",
        ]
        # default config
        config = {
            'mapping': {
            } , # Company and analytic
            'log_format': None,
            'log_file': "log.log",
            'log_level': 'INFO',
            'sleep': 5,  # time to sleep in seconds
            'channel': "",  # set the channel
            'messagetmp': "{} \n <{}>"
        }
        with open(config_file) as file:
            data = json.load(file)
            config.update(data)
        if not config['log_format']:
            config['log_format'] = ' '.join(log_format)
        if config.get('token') is None:
            raise Exception("SlackBotToken not found in config")
        return config

    def _reload_config(self, config_file):
        self.config = self._load_config(config_file)
        self.log.info('Reloaded config')
        self.log.debug('Config: %s', self.config)

    # def __signal_stop_handler(self, signum, frame):
    #     # no time-consuming actions here!
    #     # just also sys.stderr.write is a bad idea
    #     self.running = False  # stop endless loop
    #     self.end_event.set()  # wake from sleep
    #
    # def __signal_reload_handler(self, signum, frame):
    #     # no time-consuming actions here!
    #     # just also sys.stderr.write is a bad idea
    #     self.reload_event.set()
    #
    # def __setup_signal_handlers(self):
    #     signal.signal(signal.SIGTERM, self.__signal_stop_handler)
    #     signal.signal(signal.SIGINT, self.__signal_stop_handler)
    #     signal.signal(signal.SIGHUP, self.__signal_reload_handler)

    def run(self):
        self.log.info('EmailDaemon.run: starting email bot')
        print(1)
        try:
            self.running = True
            while self.running:
                self.email.email_reader()
                # sleep until timeout or end_event set
                # look for self.__signal_stop_handler
                self.end_event.wait(timeout=self.config['sleep'])
                # and just catch reload after all work on iteration
                if self.reload_event.is_set():
                    self._reload_config(self.config_file)
                    self.reload_event.clear()
        except BaseException:
            exception = sys.exc_info()
            error_tpl = 'EmailDaemon.run: unexpected error {0} {1} {2}'
            self.log.error(error_tpl.format(*exception), exc_info=True)
        finally:
            self.log.info('EmailDaemon.run: shutting down')


if __name__ == "__main__":
    conf = sys.argv[1] if len(sys.argv) > 1 else './config.json'
    slackBot = EmailDaemon(conf)
    slackBot.run()
