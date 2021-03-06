import importlib
import logging

from connectors.meta import PasswordUpdateError
from connectors.xwiki import XWikiConnector
from reports import ReportManager
from resource import Resource
from secrets import token_urlsafe


class RenewHelper:
    logger = logging.getLogger('RenewHelper')

    def __init__(self, configManager, keyringManager, passboltServer):
        self.configManager = configManager
        self.keyringManager = keyringManager
        self.passboltServer = passboltServer

    def run(self, args):
        # First try to authenticate
        if self.passboltServer.api.authenticate(self.keyringManager.keyring,
                                                self.configManager.user()['fingerprint'],
                                                self.configManager.server()['fingerprint']):
            resources = self.__fetchResources(args)

            reportManager = ReportManager(self.configManager, args)
            # Initialize a map that will contain the statistics of the renewal
            renewalStats = {
                'foundItems': 0,
                'renewableItems': 0,
                'items': {
                    'success': [],   # Successfully renewed, no problem
                    'failures': [],  # The service did not accept the renewal
                    'rollback': [],  # The password was renewed but not committed to passbolt, so it has been rollbacked
                    'errors': []     # Everything failed, including the rollback of the password
                }
            }

            # In the case where we are renewing resources that belong to a group, we will need
            # to filter which resources are shared with edit rights, and which resources are not shared with
            # this right
            if not args.personal:
                self.logger.info('Found [{}] resources available'.format(len(resources)))
                renewalStats['foundItems'] = len(resources)
                resources = self.passboltServer.filterUpdatableResources(resources)

            self.logger.info('Found [{}] resources that can be renewed'.format(len(resources)))

            if args.limit != 0 and len(resources) >= args.limit:
                self.logger.info('Limiting renewal to the first [{}] resources'.format(args.limit))
                resources = resources[:len(resources) - args.limit]

            renewalStats['renewableItems'] = len(resources)

            try:
                for resource in resources:
                    self.__renewResource(resource, args, renewalStats)
            except KeyboardInterrupt:
                self.logger.info('Interrupted, sending report and exiting ...')

            # At the end of the process, show and / or send a report
            reportManager.sendReports(renewalStats)
        else:
            self.logger.error('Failed to authenticate to the Passbolt server.')

    def __renewResource(self, resource, args, renewalStats):
        resourceID = resource['Resource']['id']
        resourceName = resource['Resource']['name']
        self.logger.debug('Renewing resource "{}"'.format(resourceName, resourceID))

        # Generate the new password
        newPassword = token_urlsafe(32)

        connector = self.__createConnector(resource, newPassword)
        if connector:
            try:
                if not args.dryRun:
                    connector.updatePassword()

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
                    group = self.passboltServer.api.groups.get(resourceGroupID)
                    self.keyringManager.maybeImportGroupUsers(group['GroupUser'])
                    for groupUser in group['GroupUser']:
                        resourceUsersMap[groupUser['User']['id']] = groupUser['User']['Gpgkey']['key_id']

                # TODO : Add user cache
                for resourceUserID in resourceUserIDs:
                    # The user might also be in a group, in that case, it's useless to add it twice
                    if resourceUserID not in resourceUsersMap:
                        user = self.passboltServer.api.users.get(resourceUserID)
                        self.keyringManager.maybeImportUser(user)
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
                        'data': self.keyringManager.keyring.encrypt(newPassword, userKeyID).data.decode('utf-8')
                    })

                if not args.dryRun:
                    if self.passboltServer.updateResource(resourceID,
                                                          resource.generateDescription(), secretsPayload):
                        self.logger.info('Resource [{}] successfully renewed and updated'.format(resourceName))
                        renewalStats['items']['success'].append({'resource': resource})
                    else:
                        self.logger.error('Failed to renew resource "{}" [{}], rolling back ...'
                                          .format(resourceName, resourceID))
                        if connector.rollbackPasswordUpdate():
                            self.logger.info('Password successfully rolled back')
                            renewalStats['items']['rollback'].append({'resource': resource})
                        else:
                            self.logger.error('''*** Heads up ! *** Password has been updated on the service,
but could not be saved on Passbolt. Password rollback also failed.''')
                            self.logger.error(secretsPayload)
                            renewalStats['items']['errors'].append({'resource': resource,
                                                                    'payload': secretsPayload})
                else:
                    self.logger.info('Skipping the update of [{}] on Passbolt as dry-run is activated'
                                     .format(resourceName))
                    renewalStats['items']['success'].append({'resource': resource})
            except PasswordUpdateError as e:
                self.logger.error('Failed to renew resource [{}] : [{}]'.format(resourceName, e))
                renewalStats['items']['failures'].append({'resource': resource})
        elif resource.connectorType is not None:
            self.logger.info('Skipping resource [{}] as no connector is available.'.format(resourceName))
        else:
            self.logger.info('Skipping resource [{}] as no connector is defined.'.format(resourceName))

    """
    Takes care of fetching every resource corresponding to the given criterias. Each resource will then be
    wrapped in a Resource() to add specific methods for updating the resource metadata.
    """
    def __fetchResources(self, args):
        if args.personal:
            rawResources = self.passboltServer.api.resources.get(
                params={'contain[permissions.group]': 1,
                        'contain[permission.user.profile]': 1,
                        'contain[secret]': 1,
                        'filter[is-owned-by-me]': 1}
            )
        else:
            self.logger.debug('Resolving groups members')
            groups = self.passboltServer.resolveGroupsByName(args.group)

            # Get every password corresponding to the groups
            groupsIDs = [x['Group']['id'] for x in groups]
            self.logger.debug('Groups IDs : [{}]'.format(groupsIDs))
            rawResources = self.passboltServer.fetchResourcesForGroups(groupsIDs)

        # Make sure that we wrap the resources in our super Resource object
        # also remove every resource having a date not valid
        # if we renew personal passwords, we also exclude resources shared with more than 1 person (the user itself)
        filteredResources = []
        for rawResource in rawResources:
            resource = Resource(rawResource)

            hasValidPerms = (True if (not args.personal or len(resource['Permission']) == 1) else False)
            hasValidDate = False
            if (args.before or args.after) and resource.lastUpdateDate is not None:
                if ((not args.before or resource.lastUpdateDate <= args.before)
                   and (not args.after or resource.lastUpdateDate >= args.after)):
                    hasValidDate = True
            else:
                # Assume that the password needs to be initialized
                hasValidDate = True

            if hasValidDate and hasValidPerms:
                filteredResources.append(resource)

        return filteredResources

    def __createConnector(self, resource, newPassword):
        # Decrypt the old password
        oldPassword = str(self.keyringManager.keyring.decrypt(resource['Secret'][0]['data']))

        if resource.connectorType is None:
            return None
        else:
            # Go through the connectors that we have registered in the configuration.
            # If we find one that fits our connectorType, instantiate it.
            for connectorName in self.configManager.connectors():
                connector = self.configManager.connectors()[connectorName]
                if connector['alias'] == resource.connectorType:
                    connectorModule = importlib.import_module('connectors.{}'.format(connectorName))
                    connectorClass = getattr(connectorModule, connector['class'])
                    return connectorClass(self.configManager, resource, oldPassword, newPassword)

            self.logger.warning('Could not find any connector with alias [{}].'.format(resource.connectorType))
            return None
