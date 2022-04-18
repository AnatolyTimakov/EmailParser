import slack

class SlackManager():
    def __init__(self, channel, messagetmp, token):
        self.client = slack.WebClient(token=token)
        self.channel = channel
        self.messagetmp = messagetmp
    def sendMessage(self, message, user):
        self.client.chat_postMessage(channel="#mailbot", text=self.messagetmp.format(message, user))