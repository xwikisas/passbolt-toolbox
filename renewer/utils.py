# Define a set of utility fuctions for the renewer
import argparse
import logging
import sys

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
        help='setup the tool to work on a specific Passbolt instance'
    )

    # Renew utils
    renewParser = subParsers.add_parser(
        'renew',
        help='renew a set of passwords'
    )
    renewParser.add_argument('filter', help='a filter to apply on the list of passwords to renew')
    renewParser.add_argument('-l', '--limit', help='only update the n first passwords')

    return rootParser.parse_args()
