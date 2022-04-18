import email
import imaplib
from email.header import make_header, decode_header
from TestBot import SlackManager

class email_manager():
    def __init__(self, logger, config):
        self.log = logger
        self.config = config
        self.slack = SlackManager(self.config['channel'], self.config['messagetmp'], self.config['token'])

    def email_reader(self):
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login('mail address', 'password')
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
            subject = str(make_header(decode_header(email_message['Subject'])))
            mail_headers.append(subject)
            self.log.debug('New mail subject: ' + subject)

            # TODO: Fix mail body decoding as mail headers
            if email_message.is_multipart():
                buff_body = []
                for payload in email_message.get_payload():
                    body = payload.get_payload(decode=True).decode('utf-8')
                    buff_body.append(body)
                mail_body.append(buff_body)
            else:
                mail_body.append(email_message.get_payload(decode=True).decode('utf-8'))

        for company, user in self.config['mapping'].items():
            company_byte = bytes(company, 'cp1251')
            company_decode = company_byte.decode('utf-8')
            for header in mail_headers:
                self.log.debug('Test ' + str(company_decode) + header)
                if company_decode in header:
                    self.log.debug('Try to send slack message {} for {}'.format(header, user))
                    self.slack.sendMessage(header, user)
                    break