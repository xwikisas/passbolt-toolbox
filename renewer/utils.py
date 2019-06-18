# Define a set of utility fuctions for the renewer
import argparse
import logging
import sys

from distutils.util import strtobool

from gpgauth import GPGAuthSessionWrapper

from configuration import Environment

def init_logger(logLevel):
    rootLogger = logging.getLogger()

    if (logLevel >= 1):
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    rootLogger.addHandler(handler)

def parse_args():
    rootParser = argparse.ArgumentParser(
        prog='passbolt-renewer',
        description='Auto-renew passwords coming from Passbolt on various services.'
    )
    rootParser.add_argument('-v', '--verbose', action='count', default=0, help='enable verbose logs')

    subParsers = rootParser.add_subparsers(
        dest='action',
        required=True,
        help='the action to perform'
    )

    # Setup utils
    setupParser = subParsers.add_parser(
        'setup',
        help='setup the tool to work on a specific Passbolt server'
    )

    # Test utils
    testParser = subParsers.add_parser(
        'test',
        help='verify the tool configuration by authenticating to the configured Passbolt server'
    )

    # Renew utils
    renewParser = subParsers.add_parser(
        'renew',
        help='renew a set of passwords'
    )
    renewParser.add_argument('filter', help='a filter to apply on the list of passwords to renew')
    renewParser.add_argument('-l', '--limit', help='only update the n first passwords')

    return rootParser.parse_args()

def display_trust_instructions(logger, fingerprint):
    logger.info('Please run the following to trust the key : ')
    commandLine = '> gpg --homedir {} --edit-key {}'.format(Environment.keyringDir, fingerprint)
    logger.info(commandLine)
    logger.info('> trust')
    logger.info('> 5')
    logger.info('> y')
    logger.info('> save')

def ask_question(question, defaultReturn):
    sys.stdout.write(question)
    try:
        return strtobool(input())
    except ValueError as e:
        return defaultReturn

def test_configuration(logger, configuration, keyring):
    serverURI = configuration.server()['uri']
    serverFingerprint = configuration.server()['fingerprint']
    serverVerifyCert = configuration.server()['verifyCert']
    userFingerprint = configuration.user()['fingerprint']
    logger.info('Testing the authentication to the server [{}]'.format(serverURI))

    session = GPGAuthSessionWrapper(
        gpg=keyring,
        server_url=serverURI,
        user_fingerprint=userFingerprint,
        verify=serverVerifyCert
    )

    assert session.server_fingerprint == serverFingerprint
    session.authenticate()

    if session.is_authenticated_with_token:
        logger.info('Success!')
    else:
        logger.info('Failed to authenticate to the server.')
