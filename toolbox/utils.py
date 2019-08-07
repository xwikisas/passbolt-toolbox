# Define a set of utility fuctions for the toolbox
import argparse
import logging
import sys

from datetime import datetime
from distutils.util import strtobool

from gpgauth import GPGAuthSessionWrapper


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
        prog='passbolt-toolbox',
        description='Toolbox to interact with various Passbolt-related services.'
    )
    rootParser.add_argument('-v', '--verbose', action='count', default=0, help='enable verbose logs')

    subParsers = rootParser.add_subparsers(
        dest='action',
        required=True,
        help='the action to perform'
    )

    # Setup utils
    subParsers.add_parser(
        'setup',
        help='setup the tool to work on a specific Passbolt server'
    )

    # Test utils
    subParsers.add_parser(
        'test',
        help='verify the tool configuration by authenticating to the configured Passbolt server'
    )

    # Renew utils
    renewParser = subParsers.add_parser(
        'renew',
        help='renew a set of passwords'
    )
    renewScope = renewParser.add_mutually_exclusive_group()
    renewScope.add_argument('-p', '--personal',
                            action='store_true',
                            help='only renew personal passwords that are not shared with anybody')
    renewScope.add_argument('-g', '--group',
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
                             default=0,
                             help='only update the n first passwords')
    renewParser.add_argument('-mr', '--mail-report',
                             dest='mailReportRecipient',
                             metavar='RECIPIENT',
                             help='send a report of the renewal by email to the given adresses')
    renewParser.add_argument('--dry-run',
                             dest='dryRun',
                             action='store_true',
                             help='run through the renewal process without actually updating resources')

    importParser = subParsers.add_parser(
        'import',
        help='import a CSV file on the Passbolt Server'
    )

    importParser.add_argument(
        '--auto-create-groups',
        dest='autoCreateGroups',
        action='store_true',
        help='if some groups are mentionned in the CSV but are not present, create them automatically'
    )

    importParser.add_argument(
        '--skip-if-exists',
        dest='skipIfExists',
        action='store_true',
        help='skip if a password with the same name accessible by the user already exists on the server'
    )

    importParser.add_argument(
        '--default-group-admins',
        type=valid_id_list,
        default=[],
        dest='defaultGroupAdmins',
        help='a comma-separated list of the user IDs to add as admin when creating the groups'
    )

    importParser.add_argument(
        '--default-group-members',
        type=valid_id_list,
        default=[],
        dest='defaultGroupMembers',
        help='a comma-separated list of the user IDs to add as member when creating the groups'
    )

    importParser.add_argument(
        'file',
        help='a path to the CSV file that needs to be imported'
    )

    importParser.add_argument(
        'outputFile',
        help='the name of the output CSV file containing the links to the created resources'
    )

    return rootParser.parse_args()

def valid_id_list(string):
    return string.split(',')

def valid_date(string):
    try:
        return datetime.strptime(string, "%m/%Y")
    except ValueError:
        msg = "Not a valid date: [{}].".format(string)
        raise argparse.ArgumentTypeError(msg)


def ask_question(question, defaultReturn):
    sys.stdout.write(question)
    try:
        return strtobool(input())
    except ValueError:
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
