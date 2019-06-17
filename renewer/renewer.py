#!/usr/bin/env python3

import argparse
import logging

from gnupg import GPG

from configuration import ConfigManager
from configuration import Environment
from setup import SetupHelper

from utils import init_logger
from utils import parse_args

args = parse_args()
init_logger(args.verbose)
logger = logging.getLogger('Main')

logger.debug('Arguments : {}'.format(args))

cm = ConfigManager()
keyring = GPG(homedir=Environment.keyringDir)

if args.action == 'setup':
    SetupHelper(cm, keyring).setupInstance()

