import logging

from configuration import Environment

from connectors.xwiki import XWikiConnector

from secrets import token_urlsafe

class RenewHelper:
    logger = logging.getLogger('RenewHelper')

    def __init__(self, configManager, keyring, passboltServer):
        self.configManager = configManager
        self.keyring = keyring
        self.passboltServer = passboltServer

        # Use to manage which keys are part of the local keyring 
        self.addedKeysCache = []
        self.keysInKeyring = []

        # User cache
        self.usersCache = {}

        # Group cache
        self.groupUsersCache = {}

    def run(self, args):
        if self.passboltServer.authenticate(self.configManager.user()['fingerprint']):
            self.logger.debug('Resolving group members')
            groups = self.passboltServer.resolveGroupsByName([args.groups])
     
            # Get the keys in the keyring
            self.keysInKeyring = [x['keyid'][-8:] for x in self.keyring.list_keys()]

            #for group in groups:
            #    self.logger.debug('Considering group [{}]'.format(group['Group']['name']))
            #    for user in group['GroupUser']:
            #        userKeyID = user['User']['Gpgkey']['key_id']
            #        self.logger.debug('Considering user [{} {}] ({})'
            #                     .format(user['User']['Profile']['first_name'],
            #                             user['User']['Profile']['last_name'],
            #                             userKeyID))
            #        if (userKeyID not in keysInKeyring and userKeyID not in addedKeysCache):
            #            self.logger.debug('Adding user key in keyring ...')
            #            importResult = self.keyring.import_keys(user['User']['Gpgkey']['armored_key'])
            #            if not importResult:
            #                raise ImportError('Failed to import GPG Key [{}] in the keyring.'
            #                                  .format(userKeyID))
            #            else:
            #                addedKeysCache.append(userKeyID)

            # Step 2 : Get every password corresponding to the groups
            groupsIDs = [x['Group']['id'] for x in groups]
            self.logger.debug('Groups IDs : [{}]'.format(groupsIDs))

            resources = self.passboltServer.fetchResourcesForGroups(groupsIDs)

            for resource in resources:
                self.logger.debug('Renewing resource [{}]'.format(resource['Resource']['id']))
                newPassword = token_urlsafe(32)

                if self.__renewResource(resource, newPassword):
                    self.logger.debug('Renew success ! Updating resource ...')
                    # Get a map of users having access to the resource + their pubkey
                    resourceUsersMap = {}

                    # List the groups to which this resource belongs
                    resourceGroupIDs = []
                    for permissionSet in resource['Permission']:
                        if permissionSet['aro'] == 'Group':
                            resourceGroupIDs.append(permissionSet['Group']['id'])
                    # TODO : Do the same for users
                    # Resolve users in the given groups
                    # TODO : Add group cache
                    for resourceGroupID in resourceGroupIDs:
                        group = self.passboltServer.fetchGroupByID(resourceGroupID)
                        self.__maybeImportGroupUsers(group['GroupUser'])
                        for groupUser in group['GroupUser']:
                            resourceUsersMap[groupUser['User']['id']] = groupUser['User']['Gpgkey']['key_id']
                    
                    # We now have a map of user IDs with their key ID, that way we can proceed to
                    # the encryption of the new password.
                    secretsPayload = []
                    for userID in resourceUsersMap.keys():
                        # Encrypt the password
                        userKeyID = resourceUsersMap[userID]
                        self.logger.debug('Encrypting password for user {} ({})'
                                          .format(userID, userKeyID))
                        secretsPayload.append({
                            'user_id': userID,
                            'data': self.keyring.encrypt(newPassword, userKeyID).data.decode('utf-8')
                        })
                    self.passboltServer.updatePassword(resource['Resource']['id'], secretsPayload)

        else:
            self.logger.error('Failed to authenticate to the Passbolt server.')

    def __renewResource(self, resource, newPassword):
        connector = XWikiConnector(resource, 'oldPassword', newPassword)
        return connector.updatePassword()

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
                    self.logger.error('Failed to import key [{}] in the keyring'
                                      .format(groupUserKeyId))
                    # TODO : Do something, throw an error ?
