import logging

from passboltapi.meta import PassboltAPI
from passboltapi.meta import PassboltAPIError


class PassboltServer:
    """Defines a Passbolt instance with its fingerprint, its url, ..."""

    logger = logging.getLogger('PassboltServer')

    """
    Builds and inits the passboltServer
    """
    def __init__(self, configManager, keyring):
        self.configManager = configManager
        self.keyring = keyring
        self.fingerprint = self.configManager.server()['fingerprint']

        # Initialize the passbolt API
        self.api = PassboltAPI({
            'serverFingerprint': self.configManager.server()['fingerprint'],
            'keyring': self.keyring,
            'uri': self.configManager.server()['uri'],
            'verifyCert': self.configManager.server()['verifyCert']
        })

        self.csrfToken = None
        self.cachedUserID = None
        self.cachedGroupIDs = None

    def __str__(self):
        return '> Server URI : {}\n> Server fingerprint : {}\n'.format(self.api.uri, self.fingerprint)

    def fetchServerIdentity(self):
        if not self.api.uri:
            raise ValueError('The server URI is undefined.')

        try:
            jsonResponse = self.api.auth.get()
            self.fingerprint = jsonResponse['body']['fingerprint']
            self.publicKey = jsonResponse['body']['keydata']
            self.logger.debug('Server public key : [{}]'.format(self.publicKey))
        except PassboltAPIError as e:
            self.logger.error('Failed to get the identity of the server.')
            self.logger.debug('Server response : [{}]'.format(e))

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
        serverConfiguration['uri'] = self.api.uri
        serverConfiguration['verifyCert'] = self.api.verifyCert
        self.configManager.persist()

    def resolveGroupsByName(self, groupNames):
        serverGroups = self.api.groups.get()
        resolvedGroups = []

        # Lower each of the group names to reduce the risk of failed maching due to bad case
        groupNames = [x.lower() for x in groupNames]

        for currentGroup in serverGroups:
            currentGroupName = currentGroup['Group']['name']
            self.logger.debug('Looking at group [{}]'.format(currentGroupName))
            if currentGroupName.lower() in groupNames:
                resolvedGroups.append(currentGroup)

        if len(resolvedGroups) == 0:
            raise ValueError('No group found with name [{}].'.format(groupNames))
        else:
            return resolvedGroups

    def fetchResourcesForGroups(self, groupIDs):
        return self.api.resources.get(
            params={'contain[permissions.group]': 1,
                    'contain[permission.user.profile]': 1,
                    'contain[secret]': 1,
                    'filter[is-shared-with-group]': groupIDs}
        )

    """
    Will return a list of groups for which the current user is in (as a standard user or as a manager.)
    This list will only be made from group IDs in a table. Returns None if the group list could not be fetched.
    """
    def fetchCurrentUserGroups(self):
        if self.cachedGroupIDs:
            return self.cachedGroupIDs

        groupsJson = self.api.groups.get(
            params={'contain[my_group_user]': 1}
        )

        self.cachedGroupIDs = []
        for element in groupsJson:
            if 'MyGroupUser' in element.keys():
                # We use also this to cache the current user ID if possible
                if self.cachedUserID is None:
                    self.cachedUserID = element['MyGroupUser']['user_id']
                self.cachedGroupIDs.append(element['Group']['id'])
        return self.cachedGroupIDs

    def filterUpdatableResources(self, resources):
        # We need to get a list of resources in which the user is in, because if we encounter a resource shared with
        # a group with edit rights, then we'll be super happy to know if our current user is part of this group.
        # https://github.com/passbolt/passboltapi/blob/master/src/Model/Entity/Permission.php#L36

        # First, make sure that we know the current user ID and the group IDs the user is in
        if self.cachedUserID is None or self.cachedGroupIDs is None:
            self.fetchCurrentUserGroups()

        filteredResources = []
        for resource in resources:
            hasUserWriteAccess = False
            for permissionSet in resource['Permission']:
                if (((permissionSet['aro'] == 'Group' and permissionSet['aro_foreign_key'] in self.cachedGroupIDs)
                    or (permissionSet['aro'] == 'User' and permissionSet['aro_foreign_key'] == self.cachedUserID))
                    # Check for UPDTATE or OWNER rights
                   and (permissionSet['type'] == 7 or permissionSet['type'] == 15)):
                    hasUserWriteAccess = True

            # Check for write access and if the resource has a connector defined
            if hasUserWriteAccess and resource.connectorType is not None:
                filteredResources.append(resource)

        return filteredResources

    def updateResource(self, resourceID, description, secretsPayload):
        payload = {'description': description, 'secrets': secretsPayload}
        self.logger.debug('Will update resource with payload : [{}]'.format(payload))

        try:
            self.api.resources.put(resourceID, data=payload)

            self.logger.debug('Successfully updated resource [{}]'.format(resourceID))
            return True
        except PassboltAPIError as e:
            self.logger.error('Failed to update the password [{}] on Passbolt !'.format(resourceID))
            self.logger.debug(e)
            return False

    def createResource(self, resource, resourceUsersMap):
        payload = {'description': description, 'secrets': secretsPayload}
        self.logger.debug('Will update resource with payload : [{}]'.format(payload))

        try:
            self.api.resources.put(resourceID, data=payload)

            self.logger.info('Successfully updated resource [{}]'.format(resourceID))
            return True
        except PassboltAPIError as e:
            self.logger.error('Failed to update the password [{}] on Passbolt !'.format(resourceID))
            self.logger.debug(e)
            return False
