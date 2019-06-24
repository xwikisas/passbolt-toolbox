import json
import logging
import requests

from requests.utils import dict_from_cookiejar

from gpgauth import GPGAuthSessionWrapper


# Defines a Passbolt instance with its fingerprint, its url, ...
class PassboltServer:
    logger = logging.getLogger('PassboltServer')

    def __init__(self, configManager, keyring):
        self.configManager = configManager
        self.keyring = keyring
        self.fingerprint = self.configManager.server()['fingerprint']
        self.uri = self.configManager.server()['uri']
        self.verifyCert = self.configManager.server()['verifyCert']
        self.csrfToken = None

    def __str__(self):
        return '> Server URI : {}\n> Server fingerprint : {}\n'.format(self.uri, self.fingerprint)

    def __buildURI(self, path):
        return '{}/{}'.format(self.uri, path)

    def __buildHeaders(self):
        baseHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.csrfToken:
            baseHeaders['X-CSRF-TOKEN'] = self.csrfToken
        return baseHeaders

    def __updateCSRFToken(self):
        self.csrfToken = dict_from_cookiejar(self.session.cookies)['csrfToken']

    def setURI(self, uri):
        self.uri = uri

    def setVerifyCert(self, verifyCert):
        self.verifyCert = verifyCert

    def fetchServerIdentity(self):
        if not self.uri:
            raise ValueError('The server URI is undefined.')

        serverResponse = requests.get(
            self.__buildURI('/auth/verify.json'),
            headers=self.__buildHeaders(),
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
            self.logger.info('The key [{}] has been imported in the keyring'.format(self.fingerprint))
        else:
            self.logger.error('Something went wrong : [{}] keys were imported in the keyring'
                              .format(importResult.counts['imported']))
            self.logger.error('The key to import might already be present in the keyring')
            # TODO: Check if the key was present before

    """
    Save the server configuration.
    """
    def persist(self):
        serverConfiguration = self.configManager.server()
        serverConfiguration['fingerprint'] = self.fingerprint
        serverConfiguration['uri'] = self.uri
        serverConfiguration['verifyCert'] = self.verifyCert
        self.configManager.persist()

    """
    Perform the GPGAuth authentication against the server. Returns True if the authentication is successful,
    False otherwise.
    """
    def authenticate(self, userFingerprint):
        self.session = GPGAuthSessionWrapper(
            gpg=self.keyring,
            server_url=self.uri,
            user_fingerprint=userFingerprint,
            verify=self.verifyCert
        )

        assert self.session.server_fingerprint == self.fingerprint
        self.session.authenticate()

        return self.session.is_authenticated_with_token

    def fetchUserByID(self, userID):
        serverResponse = self.session.get(
            self.__buildURI('/users/{}.json'.format(userID)),
            headers=self.__buildHeaders(),
            verify=self.verifyCert
        )

        return serverResponse.json()['body']

    def fetchGroupByID(self, groupID):
        serverResponse = self.session.get(
            self.__buildURI('/groups/{}.json'.format(groupID)),
            headers=self.__buildHeaders(),
            verify=self.verifyCert
        )

        return serverResponse.json()['body']

    def resolveGroupsByName(self, groupNames):
        # Start by getting the list of groups on the server
        serverResponse = self.session.get(
            self.__buildURI('/groups.json'),
            headers=self.__buildHeaders(),
            verify=self.verifyCert
        )
        resolvedGroups = []

        # Lower each of the group names to reduce the risk of failed maching due to bad case
        groupNames = [x.lower() for x in groupNames]

        # Find the correct group name
        # XXX : Verify server response
        jsonResponse = serverResponse.json()['body']

        for currentGroup in jsonResponse:
            currentGroupName = currentGroup['Group']['name']
            self.logger.debug('Looking at group [{}]'.format(currentGroupName))
            if currentGroupName.lower() in groupNames:
                resolvedGroups.append(currentGroup)

        if len(resolvedGroups) == 0:
            raise ValueError('No group found with name [{}].'.format(groupNames))
        else:
            return resolvedGroups

    def fetchResourcesForGroups(self, groupIDs):
        serverResponse = self.session.get(
            self.__buildURI('/resources.json'),
            params={'contain[permissions.group]': 1,
                    'contain[permission.user.profile]': 1,
                    'contain[secret]': 1,
                    'contain[tag]': 1,
                    'filter[is-shared-with-group]': groupIDs},
            headers=self.__buildHeaders(),
            verify=self.verifyCert
        )
        self.__updateCSRFToken()

        return serverResponse.json()['body']

    def updateResource(self, resourceID, description, secretsPayload):
        payload = {'description': description, 'secrets': secretsPayload}
        self.logger.debug('Will update resource with payload : [{}]'.format(payload))

        serverResponse = self.session.put(
            self.__buildURI('/resources/{}.json'.format(resourceID)),
            data=json.dumps(payload),
            headers=self.__buildHeaders(),
            verify=self.verifyCert
        )

        if serverResponse.status_code == 200:
            self.logger.info('Successfully updated resource [{}]'.format(resourceID))
        else:
            self.logger.error('Failed to update the password [{}] !'.format(resourceID))
            self.logger.error('Encrypted payload : [{}]'.format(secretsPayload))
            self.logger.debug(vars(serverResponse))
