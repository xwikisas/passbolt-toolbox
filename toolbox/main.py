#!/usr/bin/env python3

import logging

from gnupg import GPG

from configuration import ConfigManager
from configuration import Environment
from passbolt import PassboltServer
from setup import SetupHelper
from renew import RenewHelper

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
    # setupHelper.setupUser()
elif args.action == 'test':
    test_configuration(logger, configManager, keyring)
elif args.action == 'renew':
    RenewHelper(configManager, keyring, passboltServer).run(args)
