#!/usr/bin/env python3

import argparse
import logging

from gnupg import GPG

from configuration import ConfigManager
from configuration import Environment
from passbolt import PassboltServer
from setup import SetupHelper

from utils import init_logger
from utils import parse_args
from utils import test_configuration

args = parse_args()
init_logger(args.verbose)
logger = logging.getLogger('Main')

logger.debug('Arguments : {}'.format(args))

configManager = ConfigManager()
keyring = GPG(gnupghome=Environment.keyringDir)
passboltServer = PassboltServer(configManager, keyring)

if args.action == 'setup':
    setupHelper = SetupHelper(configManager, keyring)
    setupHelper.setupServer()
    # The user setup is not working yet, so we don't use it
    #setupHelper.setupUser()
elif args.action == 'test':
    test_configuration(logger, configManager, keyring)
elif args.action == 'renew':
    if passboltServer.authenticate(configManager.user()['fingerprint']):
        logger.debug('Resolving group members')
        groups = passboltServer.resolveGroupsByName(['Automated Update Test Group'])
        
        # STEP 1 : Make sure that we have everyone's public key

        # Get the keys in the keyring
        keysInKeyring = [x['keyid'][-8:] for x in keyring.list_keys()]
        addedKeysCache = []
        logger.debug(keysInKeyring)

        for group in groups:
            logger.debug('Considering group [{}]'.format(group['Group']['name']))
            for user in group['GroupUser']:
                userKeyId = user['User']['Gpgkey']['key_id']
                logger.debug('Considering user [{} {}] ({})'
                             .format(user['User']['Profile']['first_name'],
                                     user['User']['Profile']['last_name'],
                                     userKeyId))
                if (userKeyId not in keysInKeyring and userKeyId not in addedKeysCache):
                    logger.debug('Adding user key in keyring ...')
                    importResult = keyring.import_keys(user['User']['Gpgkey']['armored_key'])
                    if not importResult:
                        raise ImportError('Failed to import GPG Key [{}] in the keyring.'
                                          .format(userKeyId))
                    else:
                        addedKeysCache.append(userKeyId)

        # Step 2 : Get every password corresponding to the groups

        

    else:
        logger.error('Failed to authenticate to the Passbolt server.')


