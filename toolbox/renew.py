import logging

from connectors.xwiki import XWikiConnector
from resource import Resource
from secrets import token_urlsafe


class RenewHelper:
    logger = logging.getLogger('RenewHelper')

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

            if args.limit != 0 and len(resources) >= args.limit:
                self.logger.info('Limiting renewal to the first [{}] resources'.format(args.limit))
                resources = resources[:len(resources) - args.limit]

            for resource in resources:
                resourceID = resource['Resource']['id']
                resourceName = resource['Resource']['name']
                self.logger.info('Renewing resource "{}"'.format(resourceName, resourceID))

                # Generate the new password
                newPassword = token_urlsafe(32)

                connector = self.__createConnector(resource, newPassword)
                if args.dryRun or connector.updatePassword():
                    self.logger.debug('Renew success ! Updating resource on Passbolt ...')
                    resource.markAsUpdated()

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

                    # Resolve users in the given groups
                    # TODO : Add group cache
                    for resourceGroupID in resourceGroupIDs:
                        group = self.passboltServer.fetchGroupByID(resourceGroupID)
                        self.__maybeImportGroupUsers(group['GroupUser'])
                        for groupUser in group['GroupUser']:
                            resourceUsersMap[groupUser['User']['id']] = groupUser['User']['Gpgkey']['key_id']

                    # TODO : Add user cache
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
                        # Encrypt the password, create the secrets payload
                        userKeyID = resourceUsersMap[userID]
                        self.logger.debug('Encrypting password for user [{}] ({})'.format(userID, userKeyID))
                        secretsPayload.append({
                            'user_id': userID,
                            'data': self.keyring.encrypt(newPassword, userKeyID).data.decode('utf-8')
                        })

                    if args.dryRun:
                        if self.passboltServer.updateResource(resourceID,
                                                              resource.generateDescription(), secretsPayload):
                            self.logger.info('Resource "{}" renewed and updated'.format(resourceName))
                        else:
                            self.logger.error('Failed to renew resource "{}" [{}], rolling back ...'
                                              .format(resourceName, resourceID))
                            if connector.rollbackPassword():
                                self.logger.info('Password successfully rolled back')
                            else:
                                self.logger.error('''*** Heads up ! *** Password has been updated on the service,
                                but could not be saved on Passbolt. Password rollback also failed.''')
                                self.logger.error(secretsPayload)
                    else:
                        self.logger.info('Skipping the update of "{}" on Passbolt as dry-run is activated'
                                         .format(resourceName))
                else:
                    self.logger.error('Failed to renew resource "{}" [{}]'.format(resourceName, resourceID))
        else:
            self.logger.error('Failed to authenticate to the Passbolt server.')

    """
    Takes care of fetching every resource corresponding to the given criterias. Each resource will then be
    wrapped in a Resource() to add specific methods for updating the resource metadata.
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
        for rawResource in rawResources:
            resource = Resource(rawResource)

            if (args.before or args.after) and resource.lastUpdateDate is not None:
                if ((not args.before or resource.lastUpdateDate <= args.before)
                   and (not args.after or resource.lastUpdateDate >= args.after)):
                    filteredResources.append(resource)
            else:
                # Assume that the password needs to be initialized
                filteredResources.append(resource)

        return filteredResources

    def __createConnector(self, resource, newPassword):
        # Decrypt the old password
        oldPassword = self.keyring.decrypt(resource['Secret'][0]['data'])
        return XWikiConnector(resource, oldPassword, newPassword)

    def __maybeImportKey(self, armoredKey, keyID, firstName, lastName):
        if (keyID not in self.keysInKeyring
                and keyID not in self.addedKeysCache):
            self.logger.info('Importing missing public key for {} {} ({})'
                             .format(firstName, lastName, keyID))
            importResult = self.keyring.import_keys(armoredKey)
            if importResult:
                self.addedKeysCache.append(keyID)
            else:
                self.logger.error('Failed to import key [{}] in the keyring'.format(keyID))
                # TODO : Do something, throw an error ?

    def __maybeImportUser(self, user):
        self.__maybeImportKey(user['Gpgkey']['armored_key'],
                              user['Gpgkey']['key_id'],
                              user['Profile']['first_name'],
                              user['Profile']['last_name'])

    # Make sure that the given Users are present in the local keyring
    def __maybeImportGroupUsers(self, groupUsers):
        for groupUser in groupUsers:
            self.__maybeImportKey(groupUser['User']['Gpgkey']['armored_key'],
                                  groupUser['User']['Gpgkey']['key_id'],
                                  groupUser['User']['Profile']['first_name'],
                                  groupUser['User']['Profile']['last_name'])
