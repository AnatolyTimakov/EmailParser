import os
import sys
import json
import signal
import threading
import email
import imaplib
import logging
from TestBot import SlackManager
from logging.handlers import WatchedFileHandler

class EmailDaemon():
    def __init__(self, config_file, logger=None):
        self.config_file = config_file
        self.config = self._load_config(config_file)
        logging.basicConfig(format=self.config['log_format'])
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
        self.__setup_signal_handlers()

        self.slack = SlackManager(self.config['channel'], self.config['messagetmp'], self.config['token'])

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
            'log_file': None,
            'log_level': 'INFO',
            'sleep': 1, # time to sleep in seconds
            'channel': "general",
            'messagetmp': "{} \n <{}>"
        }
        with open(config_file) as file:
            data = json.load(file)
            config.update(data)
        if not config['log_format']:
            config['log_format'] = ' '.join(log_format)
        if os.environ.get('SLACK_TOKEN') is None:
            raise Exception("SlackBotToken not found in config")
        else:
            config['token'] = os.environ.get('SLACK_TOKEN')
        return config

    def _reload_config(self, config_file):
        self.config = self._load_config(config_file)
        self.log.info('Reloaded config')
        self.log.debug('Config: %s', self.config)

    def __signal_stop_handler(self, signum, frame):
        # no time-consuming actions here!
        # just also sys.stderr.write is a bad idea
        self.running = False  # stop endless loop
        self.end_event.set()  # wake from sleep

    def __signal_reload_handler(self, signum, frame):
        # no time-consuming actions here!
        # just also sys.stderr.write is a bad idea
        self.reload_event.set()

    def __setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.__signal_stop_handler)
        signal.signal(signal.SIGINT, self.__signal_stop_handler)
        signal.signal(signal.SIGHUP, self.__signal_reload_handler)

    def work(self):
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login('seceretboris@gmail.com', 'gbgbcmrf1!')
        mail.select("inbox")

        self.log.debug('Starting email part')
        mail_headers = []
        mail_body = []

        #result, data = mail.search(None, "(UNSEEN)")
        result, data = mail.search(None, "(ALL)")
        self.log.debug('Parsing email, result data')

        ids = data[0]
        id_list = ids.split()

        for id in id_list:
            result, data = mail.fetch(id, "(RFC822)")
            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')

            email_message = email.message_from_string(raw_email_string)
            mail_headers.append(email_message['Subject'])

            if email_message.is_multipart():
                buff_body = []
                for payload in email_message.get_payload():
                    body = payload.get_payload(decode=True).decode('utf-8')
                    buff_body.append(body)
                mail_body.append(buff_body)
            else:
                mail_body.append(email_message.get_payload(decode=True).decode('utf-8'))

        for company, user in self.config['mapping'].items():
            for header in mail_headers:
                self.log.debug('Email, company, user', str(company), str(user), header)
                if company in header:
                    self.log.debug('Email, company, user', str(company), str(user), header)
                    self.slack.sendMessage(header, user)
                    break
            # for text in mail_body:
            #     if company in text[0]:
            #         self.slack.sendMessage(header, user)
            #         break

    def run(self):
        self.log.info('EmailDaemon.run: starting email bot')
        print(1)
        try:
            self.running = True
            while self.running:
                self.work()
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
