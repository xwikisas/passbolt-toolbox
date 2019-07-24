import logging
import smtplib

from datetime import datetime
from email.message import EmailMessage
from jinja2 import Environment
from jinja2 import FileSystemLoader


class ReportManager:
    def __init__(self, configManager, args):
        self.config = configManager
        self.args = args

    def sendReports(self, renewalStats):
        if self.args.mailReportRecipient:
            MailReporter(self.config, self.args, renewalStats).sendReport()


"""
Simple reporting interface.
"""


class Reporter:
    logger = logging.getLogger('Reporter')

    def __init__(self, configManager, args, renewalStats):
        self.config = configManager
        self.args = args
        self.renewalStats = renewalStats

    def _renderTemplate(self, templateName):
        environment = Environment(loader=FileSystemLoader('toolbox/templates'))
        template = environment.get_template(templateName)
        renderedTemplate = template.render({
            'stats': self.renewalStats,
            'context': {
                'date': datetime.now()
            }
        })

        self.logger.debug(self.renewalStats)
        self.logger.debug('Rendered report template : [{}]'.format(renderedTemplate))
        return renderedTemplate


class MailReporter(Reporter):
    logger = logging.getLogger('MailReporter')

    def sendReport(self):
        with smtplib.SMTP(self.config.parameters()['mail']['server']) as smtp:
            smtp.starttls()
            smtp.ehlo()
            # TODO: Make that a bit more configurable
            # Currently, we are using one config that works for our use case, but that
            # might not work globally
            smtp.user = self.config.parameters()['mail']['user']
            smtp.password = self.config.parameters()['mail']['password']
            smtp.auth('LOGIN', smtp.auth_login)

            msg = EmailMessage()
            msg.set_content(self._renderTemplate('mailReport.txt'))

            msg['Subject'] = '[Passbolt Toolbox] Password renewal report'
            msg['From'] = self.config.parameters()['mail']['sender']
            msg['To'] = self.args.mailReportRecipient

            smtp.send_message(msg)
