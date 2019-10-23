import logging
import paramiko

from .meta import Connector


class HtdigestConnector(Connector):
    logger = logging.getLogger('HtdigestConnector')

    defaultConfig = {
        'use-sudo': True,
        'script-directory': '/srv/',
        'username': 'wheel',
        'domain': None
    }

    def __init__(self, configManager, resource, oldPassword, newPassword):
        super(HtdigestConnector, self).__init__(configManager, resource, oldPassword, newPassword)

        # Get the htdigest connector configuration
        self.config = self.defaultConfig
        if 'htdigest' in self.configManager.connectors().keys():
            self.config.update(self.configManager.connectors()['htdigest'])

        # Compute the domain to use, default on the URI of the server
        if self.config['domain']:
            domain = self.config['domain']
        else:
            domain = resource['Resource']['uri']

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())

    def updatePassword(self):
        # Connect to the server
        self.client.connect(resource['Resource']['uri'], username=self.config['username'])

        if self.config['use-sudo']:
            command = 'sudo {}/./update_htdigest.sh "{}" "{}" "{}"'
        else:
            command = '{}/./update_htdigest.sh "{}" "{}" "{}"'

        stdin, stdout, stderr = client.exec_command(
            command.format(self.config['script-directory'],
                           resource['Resource']['username'],
                           self.newPassword))

        self.client.close()

    def rollbackPasswordUpdate(self):
        self.client.connect(resource['Resource']['uri'], username=self.config['username'])

        if self.config['use-sudo']:
            command = 'sudo {}/./rollback_htdigest.sh'
        else:
            command = '{}/./rollback_htdigest.sh'

        stdin, stdout, stderr = client.exec_command(
            command.format(self.config['script-directory']))

        self.client.close()
