import logging
import sys

from distutils.util import strtobool

from passbolt import PassboltServer

class SetupHelper:
    logger = logging.getLogger('SetupHelper')

    def __init__(self, configManager, keyring):
        self.configManager = configManager
        self.keyring = keyring
        # Create a PassboltServer with the current configuration
        self.passboltServer = PassboltServer(configManager, keyring)

    def __askQuestion(self, question, defaultReturn):
        sys.stdout.write(question)
        try:
            return strtobool(input())
        except ValueError as e:
            return defaultReturn

    """
    Check whether the actual configuration contains a configured server.
    If so, asks to overwrite it or not.
    @return true if we can go on with the configuration
    """
    def __checkExistingConfiguration(self):
        if not self.passboltServer.fingerprint or not self.passboltServer.uri:
           return self.__askQuestion(
               'A server configuration is already present, continue ? [yes / NO] ',
               False
           )
        else:
            return True

    def __getServerURI(self):
        print('Server URI : ')
        self.passboltServer.setURI()


    def setupInstance(self):
        if self.__checkExistingConfiguration():
            # Get the server uri
            sys.stdout.write('Server URI : ')
            self.passboltServer.setURI(input())
            self.passboltServer.fetchServerIdentity()
            if self.__askQuestion(
                    'Server identity\n{}\nContinue ? [yes / NO] '.format(self.passboltServer), False):
                self.passboltServer.importServerIdentity()
                self.passboltServer.persist()
                self.logger.info('Server setup complete')
                return

        self.logger.info('Aborting.')
