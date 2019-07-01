import logging
import sys

from passbolt import PassboltServer
from utils import ask_question


class SetupHelper:
    logger = logging.getLogger('SetupHelper')

    def __init__(self, configManager, keyring):
        self.configManager = configManager
        self.keyring = keyring
        # Create a PassboltServer with the current configuration
        self.passboltServer = PassboltServer(configManager, keyring)

    def __displaySetupBanner(self, message):
        print('*************************')
        print(message)
        print('*************************')

    """
    Check whether the actual configuration contains a configured server.
    If so, asks to overwrite it or not.
    @return true if we can go on with the configuration
    """
    def __checkExistingServerConfiguration(self):
        if (self.passboltServer.fingerprint or self.passboltServer.uri):
            return ask_question(
                'A server configuration for [{}] is already present, continue ? [yes / NO] '
                .format(self.passboltServer.uri),
                False
            )
        else:
            return True

    """
    Check whether the actual configuration contains a configured user.
    If so, asks to overwrite it or not.
    @return true if we can go on with the configuration
    """
    def __checkExistingUserConfiguration(self):
        if (self.configManager.user()['fingerprint']):
            return ask_question(
                'A configuration for the user [{}] is already present, continue ? [yes / NO] '
                .format(self.configManager.user()['fingerprint']),
                False
            )
        else:
            return True

    def __getServerURI(self):
        print('Server URI : ')
        self.passboltServer.setURI()

    def setupServer(self):
        self.__displaySetupBanner('Server setup')

        if self.__checkExistingServerConfiguration():
            # Get the server uri
            sys.stdout.write('Server URI : ')
            self.passboltServer.setURI(input())

            self.passboltServer.setVerifyCert(
                not ask_question(
                    'Trust the server certficate without verification ? [yes / NO] ', False
                )
            )

            self.passboltServer.fetchServerIdentity()
            if ask_question(
                    'Server identity\n{}\nContinue ? [yes / NO] '.format(self.passboltServer), False):
                self.passboltServer.importServerIdentity()
                self.passboltServer.persist()
                self.logger.info('Server setup complete')
                return

        self.logger.info('Aborting server setup')
