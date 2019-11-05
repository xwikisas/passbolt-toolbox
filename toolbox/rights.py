import importlib
import json
import logging

from connectors.xwiki import XWikiConnector
from reports import ReportManager
from resource import Resource
from secrets import token_urlsafe


class RightsUpdateHelper:
    logger = logging.getLogger('RightsUpdateHelper')

    def __init__(self, configManager, keyringManager, passboltServer):
        self.configManager = configManager
        self.keyringManager = keyringManager
        self.passboltServer = passboltServer

    def run(self, args):
        # First try to authenticate
        if self.passboltServer.api.authenticate(self.keyringManager.keyring,
                                                self.configManager.user()['fingerprint'],
                                                self.configManager.server()['fingerprint']):
            allGroups = self.passboltServer.api.groups.get(params={'contain[group_user]': 1})

            for group in allGroups:                # Check if the group contains the user that we want to fix
                userGroupRelation = None
                for user in group['GroupUser']:
                    if user['user_id'] == args.user_id:
                        userGroupRelation = user
                        break

                # Check if the user has the correct permissions
                if userGroupRelation is not None:
                    if userGroupRelation['is_admin'] != args.is_manager:
                        self.logger.info('Updating membership of user for group [{}]'.format(group['Group']['name']))

                        # Send the updated group to the server
                        payload = {'groups_users': [{'id': userGroupRelation['id'], 'is_admin': args.is_manager}]}
                        response = self.passboltServer.api.groups.put(group['Group']['id'], json.dumps(payload))
                    else:
                        self.logger.info('Nothing to do for group [{}]'.format(group['Group']['name']))
                else:
                    self.logger.info('User [{}] not found in group [{}]'.format(args.user_id, group['Group']['name']))
