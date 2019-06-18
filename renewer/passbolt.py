import logging
import requests

from configuration import Environment

from utils import display_trust_instructions

# Defines a Passbolt instance with its fingerprint, its url, ...
class PassboltServer:
    logger = logging.getLogger('PassboltServer')

    def __init__(self, configManager, keyring):
        self.configManager = configManager
        self.keyring = keyring
        self.fingerprint = self.configManager.server()['fingerprint']
        self.uri = self.configManager.server()['uri']
        self.verifyCert = self.configManager.server()['verifyCert']

    def __str__(self):
        return '> Server URI : {}\n> Server fingerprint : {}\n'.format(self.uri, self.fingerprint)

    def __buildURI(self, path):
        return '{}/{}'.format(self.uri, path)

    def __buildHeaders(self, csrfToken):
        baseHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if csrfToken:
            baseHeaders['X-CSRF-TOKEN'] = csrfToken
        return baseHeaders

    def setURI(self, uri):
        self.uri = uri

    def setVerifyCert(self, verifyCert):
        self.verifyCert = verifyCert

    def fetchServerIdentity(self):
        if not self.uri:
            raise ValueError('The server URI is undefined.')

        serverResponse = requests.get(
            self.__buildURI('/auth/verify.json'),
            headers=self.__buildHeaders(None),
            verify=self.verifyCert
        )

        if serverResponse.status_code == 200:
            jsonResponse = serverResponse.json()
            self.fingerprint = jsonResponse['body']['fingerprint']
            self.publicKey = jsonResponse['body']['keydata']
            self.logger.debug('Server public key : [{}]'.format(self.publicKey))
        else:
            self.logger.error('Failed to get the identity of the server.')
            self.logger.debug('Server response : [{}]'.format(serverResponse.content))

    """
    This will ensure that the PGP public key of the server is correctly saved in the GPG keyring and
    will ask the user to set the correct trust level for the key.
    """
    def importServerIdentity(self):
        importResult = self.keyring.import_keys(self.publicKey)
        if importResult:
            self.logger.info(
                'The key [{}] has been imported in the keyring but needs to be trusted before use'
                .format(self.fingerprint)
            )

            display_trust_instructions(self.logger, self.fingerprint)
        else:
            self.logger.error('Something went wrong : [{}] keys were imported in the keyring'
                         .format(importResult.counts['imported']))
            self.logger.error('The key to import might already be present in the keyring')
            # TODO: Check if the key was present before

    """
    Save the configuration of the server in the configuration file.
    """
    def persist(self):
        serverConfiguration = self.configManager.server()
        serverConfiguration['fingerprint'] = self.fingerprint
        serverConfiguration['uri'] = self.uri
        serverConfiguration['verifyCert'] = self.verifyCert
        self.configManager.persist()
