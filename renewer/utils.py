# Define a set of utility fuctions for the renewer
import argparse
import logging
import sys

from distutils.util import strtobool

from gpgauth import GPGAuthSessionWrapper

from configuration import Environment

def init_logger(logLevel):
    rootLogger = logging.getLogger()
    logging.captureWarnings(True)

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
    renewParser.add_argument('-g', '--group',
                             nargs=1,
                             help='group in which the password should be included')
    renewParser.add_argument('-b', '--before',
                            type=valid_date,
                            help='date before which the password should have been updated')
    renewParser.add_argument('-a', '--after',
                             type=valid_date,
                             help='date after which the password should have been updated')
    renewParser.add_argument('-l', '--limit',
                             type=int,
                             help='only update the n first passwords')

    return rootParser.parse_args()

def valid_date(string):
    try:
        return datetime.strptime(string, "%m-%Y")
    except ValueError:
        msg = "Not a valid date: [{}].".format(string)
        raise argparse.ArgumentTypeError(msg)

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
