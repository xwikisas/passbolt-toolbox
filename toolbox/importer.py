import csv
import json
import logging

from passboltapi.meta import PassboltAPIError


class ImportHelper:
    logger = logging.getLogger('RenewHelper')

    def __init__(self, configManager, keyringManager, passboltServer):
        self.configManager = configManager
        self.keyringManager = keyringManager
        self.passboltServer = passboltServer

        self.cachedUserID = None

        self.groups = None
        self.groupNames = None

    def run(self, args):
        # First try to authenticate
        if self.passboltServer.api.authenticate(self.keyringManager.keyring,
                                                self.configManager.user()['fingerprint'],
                                                self.configManager.server()['fingerprint']):
            # Parse the CSV
            csvResources = []
            with open(args.file) as csvFile:
                spamReader = csv.reader(csvFile, delimiter=',')
                for row in spamReader:
                    self.logger.debug('Registering entry {}'.format(row))
                    csvResources.append({
                        'name': row[0],
                        'username': row[1],
                        'password': row[2],
                        'uri': row[3],
                        'description': row[4],
                        'group': row[5],
                        'page': row[6],
                        'rawtext': row[7]
                    })

            # Get a list of existing groups
            self.groups = self.passboltServer.api.groups.get()
            self.__generateGroupNames()

            resultCSV = []

            if args.skipIfExists:
                # Get a list of existing resources
                existingResources = self.passboltServer.api.resources.get()
                existingResourcesNames = [r['Resource']['Name'] for r in existingResources]

                resources = []
                for resource in csvResources:
                    if resource['name'] not in existingResourcesNames:
                        resources.append(resource)
                    else:
                        self.logger.info('Skipping resource [{}] as it is already on the server'
                                         .format(resource['name']))
            else:
                resources = csvResources

            # Debugging, only take the first 5 passwords
            resources = resources[:5]

            for resource in resources:
                # Check if the group of the resource exists or not
                if resource['group'] and resource['group'] not in self.groupNames and args.autoCreateGroups:
                    # We need to create a group
                    groupExists = self.__createGroup(resource['group'], args)
                else:
                    groupExists = args.autoCreateGroups

                if groupExists:
                    resourceID = self.__createResource(resource)

                    # Resolve users in the given groups
                    # TODO : Add group cache
                    groupID = self.__getGroupIDFromName(resource['group'])
                    if groupID:
                        group = self.passboltServer.api.groups.get(groupID)
                        self.keyringManager.maybeImportGroupUsers(group['GroupUser'])
                        resourceUsersMap = {}
                        for groupUser in group['GroupUser']:
                            resourceUsersMap[groupUser['User']['id']] = groupUser['User']['Gpgkey']['key_id']

                        # We now have a map of user IDs with their key ID, that way we can proceed to
                        # the encryption of the new password.
                        secretsPayload = []
                        for userID in resourceUsersMap.keys():
                            # Encrypt the password for the new group users
                            # We don't need to encrypt using our key
                            if userID != self.__getCurrentUserID():
                                userKeyID = resourceUsersMap[userID]
                                self.logger.debug('Encrypting password for user [{}] ({})'.format(userID, userKeyID))
                                secretsPayload.append({
                                    'user_id': userID,
                                    'resource_id': resourceID,
                                    'data': self.keyringManager.keyring.encrypt(resource['password'], userKeyID)
                                                .data.decode('utf-8')
                                })

                        # Share with a group with type "Manage"
                        # TODO: Be able to customize the share type :
                        # 1 : Read only
                        # 7 : Read / Write
                        # 15 : Manage
                        if not self.__shareResource(resourceID, groupID, 15, secretsPayload):
                            self.logger.error('Failed to share resource [{}] ({}) with group [{}] ({})'
                                              .format(resource['name'], resourceID, resource['group'], groupID))
                        else:
                            resultCSV.append([resource['page'],
                                              resource['rawtext'],
                                              '{}/app/passwords/view/{}'.format(self.configManager.server()['uri'],
                                                                                resourceID)])
                    else:
                        self.logger.error('Error while retrieving the group to share the resource with.')
                elif not args.autoCreateGroups:
                    self.logger.warning('Skipping resource [{}] as group [{}] is not already present on the server.'
                                        .format(resource['name'], resource['group']))
                else:
                    self.logger.error('Error while creating the group [{}]. Skipping resource [{}].'
                                      .format(resource['group'], resource['name']))

            if len(resultCSV) > 0:
                self.logger.info('Saving result CSV file as [{}]'.format(args.outputFile))
                with open(args.outputFile, 'w+') as f:
                    spamWriter = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
                    for row in resultCSV:
                        spamWriter.writerow(row)
        else:
            self.logger.error('Failed to authenticate to the Passbolt server.')

    def __getCurrentUserID(self):
        if self.cachedUserID:
            return self.cachedUserID
        else:
            users = self.passboltServer.api.users.get()

            for user in users:
                if user['Gpgkey']['fingerprint'] == self.configManager.user()['fingerprint']:
                    self.logger.debug(user)
                    self.cachedUserID = user['User']['id']
                    return self.cachedUserID

            self.logger.error('Failed to fetch the ID of the current user')

    def __generateGroupNames(self):
        self.groupNames = [g['Group']['name'] for g in self.groups if g['Group']['deleted'] is False]

    def __getGroupIDFromName(self, groupName):
        for group in self.groups:
            if group['Group']['name'] == groupName:
                return group['Group']['id']

        return None

    def __createResource(self, resource):
        self.logger.info('Creating resource [{}]'.format(resource['name']))

        payload = {
            'name': resource['name'],
            'description': resource['description'],
            'username': resource['username'],
            'uri': resource['uri'],
            'secrets': [{
                'user_id': self.__getCurrentUserID(),
                'data': self.keyringManager.keyring.encrypt(resource['password'], self.configManager.user()['fingerprint']).data.decode('utf-8')
            }]
        }

        try:
            result = self.passboltServer.api.resources.post(data=json.dumps(payload))
            self.logger.info(result)
            return result['id']
        except PassboltAPIError as e:
            self.logger.debug(e)

    # Share a resource with a given group
    def __shareResource(self, resourceID, groupID, type, secretsPayload):
        self.logger.debug('Sharing resource [{}] with group [{}]'.format(resourceID, groupID))
        payload = {
            'permissions': [{
                'aco': 'Resource',
                'aco_foreign_key': resourceID,
                'aro': 'Group',
                'aro_foreign_key': groupID,
                'is_new': True,
                'type': type
            }],
            'secrets': secretsPayload
        }

        try:
            self.logger.debug(json.dumps(payload))
            result = self.passboltServer.api.share.put(resourceID, data=json.dumps(payload))
            return True
        except PassboltAPIError as e:
            self.logger.debug(e)
            return False

    def __createGroup(self, groupName, args):
        self.logger.info('Creating group [{}]'.format(groupName))

        # Get the current user ID, we want to be at least member of the group to create the passwords
        currentUserID = self.__getCurrentUserID()
        self.logger.debug('Current user ID [{}]'.format(currentUserID))
        if currentUserID not in args.defaultGroupAdmins and currentUserID not in args.defaultGroupMembers:
            # Add at least the current user to the group
            # We need at least one admin in the group
            if len(args.defaultGroupAdmins) == 0:
                args.defaultGroupAdmins.append(currentUserID)
            else:
                args.defaultGroupMembers.append(currentUserID)

        # Prepare the payload for creating the groups
        groupUsers = []
        for user in args.defaultGroupAdmins:
            groupUsers.append({
                'GroupUser': {
                    'user_id': user,
                    'is_admin': 1
                }
            })
        for user in args.defaultGroupMembers:
            groupUsers.append({
                'GroupUser': {
                    'user_id': user,
                    'is_admin': 0
                }
            })

        payload = {
            'Group': {'name': groupName},
            'GroupUsers': groupUsers
        }

        try:
            self.logger.debug(json.dumps(payload))
            response = self.passboltServer.api.groups.post(data=json.dumps(payload))

            # Update the local group list to add the newly created group
            self.groups.append({'Group': response['Group']})
            self.__generateGroupNames()
            return True
        except PassboltAPIError as e:
            self.logger.debug(e)
            return False
