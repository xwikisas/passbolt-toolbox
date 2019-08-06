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

    def __init__(self, resource, oldPassword, newPassword):
        super(HtdigestConnector, self).__init__(resource, oldPassword, newPasword)

        # Get the htdigest connector configuration
        if 'htdigest' in self.configManager.connectors().keySet():
            self.config = self.configManager.connectors()['htdigest']
        else:
            self.config = self.defaultConfig

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())

    def updatePassword(self):
        # Connect to the server
        self.client.connect(resource['Resource']['uri'], username=self.config['username'])

        # Compute the domain to use, default on the URI of the server
        if self.config['domain']:
            domain = self.config['domain']
        else:
            domain = resource['Resource']['uri']

        if self.config['use-sudo']:
            command = 'sudo {}/./update_htdigest.sh "{}" "{}" "{}"'
        else:
            command = '{}/./update_htdigest.sh "{}" "{}" "{}"'

        stdin, stdout, stderr = client.exec_command(
            command.format(self.config['script-directory'],
                           resource['Resource']['username'],
                           self.newPassword))

    def rollbackPasswordUpdate(self):
        pass
