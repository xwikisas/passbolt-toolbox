#!/usr/bin/env python3

import argparse
import logging

from gnupg import GPG

from configuration import ConfigManager
from configuration import Environment
from setup import SetupHelper

from utils import init_logger
from utils import parse_args
from utils import test_configuration

args = parse_args()
init_logger(args.verbose)
logger = logging.getLogger('Main')

logger.debug('Arguments : {}'.format(args))

cm = ConfigManager()
keyring = GPG(gnupghome=Environment.keyringDir)

if args.action == 'setup':
    setupHelper = SetupHelper(cm, keyring)
    setupHelper.setupServer()
    # The user setup is not working yet, so we don't use it
    #setupHelper.setupUser()
elif args.action == 'test':
    test_configuration(logger, cm, keyring)
