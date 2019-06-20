import logging
import re

from configuration import Environment

from connectors.xwiki import XWikiConnector

from secrets import token_urlsafe

class RenewHelper:
    logger = logging.getLogger('RenewHelper')
    # Used in regex, shouldn't contain unescaped regex modifiers
    lastUpdatePattern = '^>>> Last password update : (.*)$'

    def __init__(self, configManager, keyring, passboltServer):
        self.configManager = configManager
        self.keyring = keyring
        self.passboltServer = passboltServer

        # Use to manage which keys are part of the local keyring
        self.addedKeysCache = []
        # Get the keys currently in the keyring
        self.keysInKeyring = [x['keyid'][-8:] for x in self.keyring.list_keys()]

    def run(self, args):
        if self.passboltServer.authenticate(self.configManager.user()['fingerprint']):
            resources = self.__fetchResources(args)
            self.logger.info('Found [{}] resources to renew'.format(len(resources)))

            for resource in resources:
                resourceID = resource['Resource']['id']
                resourceName = resource['Resource']['name']
                self.logger.info('Renewing resource "{}"'.format(resourceName, resourceID))

                # Generate the new password
                newPassword = token_urlsafe(32)

                if self.__renewResource(resource, newPassword):
                    self.logger.debug('Renew success ! Updating resource on Passbolt ...')
                    # Get a map of users having access to the resource + their pubkey
                    resourceUsersMap = {}

                    # List the groups to which this resource belongs
                    resourceUserIDs = []
                    resourceGroupIDs = []
                    for permissionSet in resource['Permission']:
                        if permissionSet['aro'] == 'Group':
                            resourceGroupIDs.append(permissionSet['aro_foreign_key'])
                        elif permissionSet['aro'] == 'User':
                            resourceUserIDs.append(permissionSet['aro_foreign_key'])

                    # TODO : Add user cache
                    # Resolve users in the given groups
                    # TODO : Add group cache
                    for resourceGroupID in resourceGroupIDs:
                        group = self.passboltServer.fetchGroupByID(resourceGroupID)
                        self.__maybeImportGroupUsers(group['GroupUser'])
                        for groupUser in group['GroupUser']:
                            resourceUsersMap[groupUser['User']['id']] = groupUser['User']['Gpgkey']['key_id']

                    for resourceUserID in resourceUserIDs:
                        # The user might also be in a group, in that case, it's useless to add it twice
                        if resourceUserID not in resourceUsersMap:
                            user = self.passboltServer.fetchUserByID(resourceUserID)
                            self.__maybeImportUser(user)
                            resourceUsersMap[resourceUserID] = user['Gpgkey']['key_id']

                    # We now have a map of user IDs with their key ID, that way we can proceed to
                    # the encryption of the new password.
                    secretsPayload = []
                    for userID in resourceUsersMap.keys():
                        # Encrypt the password
                        userKeyID = resourceUsersMap[userID]
                        self.logger.debug('Encrypting password for user [{}] ({})'.format(userID, userKeyID))
                        secretsPayload.append({
                            'user_id': userID,
                            'data': self.keyring.encrypt(newPassword, userKeyID).data.decode('utf-8')
                        })

                    if self.passboltServer.updateResource(resourceID, secretsPayload):
                        self.logger.info('Resource "{}" renewed and updated'.format(resourceName))
                else:
                    self.logger.error('Failed to renew resource "{}" [{}]'.format(resourceName, resourceID))
        else:
            self.logger.error('Failed to authenticate to the Passbolt server.')

    """
    Takes care of fetching every resource corresponding to the given criterias
    """
    def __fetchResources(self, args):
        self.logger.debug('Resolving group members')
        groups = self.passboltServer.resolveGroupsByName(args.group)

        # Get every password corresponding to the groups
        groupsIDs = [x['Group']['id'] for x in groups]
        self.logger.debug('Groups IDs : [{}]'.format(groupsIDs))
        rawResources = self.passboltServer.fetchResourcesForGroups(groupsIDs)

        # Remove every resource having a date not valid
        filteredResources = []
        for resource in rawResources:
            resourceDescription = resource['Resource']['description']

            if resourceDescription is not None:
                updateDateLines = re.findall(self.lastUpdatePattern, resourceDescription, re.MULTILINE)
                self.logger.error(updateDateLines)

                # We will only consider the first line with the date for filtering
                if len(updateDateLines) != 0:
                    pass
                else:
                    # Assume that the password needs to be initialized
                    filteredResources.append(resource)
            else:
                # Assume that the password needs to be initialized
                filteredResources.append(resource)

        return filteredResources

    def __renewResource(self, resource, newPassword):
        # Decrypt the old password
        oldPassword = self.keyring.decrypt(resource['Secret'][0]['data'])
        connector = XWikiConnector(resource, oldPassword, newPassword)
        return connector.updatePassword()

    def __maybeImportUser(self, user):
        userKeyId = user['Gpgkey']['key_id']
        if (userKeyId not in self.keysInKeyring
                and userKeyId not in self.addedKeysCache):
            self.logger.info('Importing missing public key for {} {} ({})'
                             .format(user['Profile']['first_name'], user['Profile']['last_name'], userKeyId))
            importResult = self.keyring.import_keys(user['Gpgkey']['armored_key'])
            if importResult:
                self.addedKeysCache.append(userKeyId)
            else:
                self.logger.error('Failed to import key [{}] in the keyring'.format(userKeyId))

    # Make sure that the given Users are present in the local keyring
    def __maybeImportGroupUsers(self, groupUsers):
        for groupUser in groupUsers:
            groupUserKeyId = groupUser['User']['Gpgkey']['key_id']
            if (groupUserKeyId not in self.keysInKeyring
                    and groupUserKeyId not in self.addedKeysCache):
                self.logger.info('Importing missing public key for {} {} ({})'
                                 .format(groupUser['User']['Profile']['first_name'],
                                         groupUser['User']['Profile']['last_name'],
                                         groupUserKeyId))
                importResult = self.keyring.import_keys(groupUser['User']['Gpgkey']['armored_key'])
                if importResult:
                    self.addedKeysCache.append(groupUserKeyId)
                else:
                    self.logger.error('Failed to import key [{}] in the keyring'.format(groupUserKeyId))
                    # TODO : Do something, throw an error ?
