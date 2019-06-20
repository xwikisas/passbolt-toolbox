import json
import logging
import os
import os.path
import stat

class Environment:
    configDir = '{}/.passbolt-renewer'.format(os.getenv('HOME'))
    configFilePath = '{}/config.json'.format(configDir)
    keyringDir = '{}/gnupg'.format(configDir)
    privateKeysDir = '{}/private-keys-v1.d'.format(keyringDir)

class ConfigManager:
    logger = logging.getLogger('ConfigManager')

    def __init__(self):
        self.__ensureExistingFolders()
        self.__ensureFolderPermissions()
        self.__ensureGPGConfiguration()
        self.__loadConfig()

    def __ensureExistingFolders(self):
        foldersToCheck = [Environment.configDir, Environment.keyringDir, Environment.privateKeysDir]

        for folder in foldersToCheck:
            self.logger.debug('Checking if directory [{}] is present'.format(folder))
            if not os.path.isdir(folder):
                self.logger.info('Creating directory [{}]'.format(folder))
                os.makedirs(folder)

    def __ensureFolderPermissions(self):
        os.chmod(Environment.privateKeysDir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    # Make sure that the trust model of GnuPG is well set so that every imported key get ultimate trust and
    # can be used for encryption / decryption
    def __ensureGPGConfiguration(self):
        gpgConfigFile = '{}/gpg.conf'.format(Environment.keyringDir)
        trustModelInstruction = 'trust-model always'

        with open(gpgConfigFile, 'a+') as f:
            fileLines = f.readlines()
            if trustModelInstruction not in fileLines:
                self.logger.info('Updating [{}] to set the GnuPG trust-model'.format(gpgConfigFile))
                f.write('\n')
                f.write('# Automatically added by Passbolt Renewer\n')
                f.write('{}\n'.format(trustModelInstruction))

    def __loadConfig(self):
        baseConfigDir = os.path.dirname(Environment.configFilePath)

        if not os.path.exists(baseConfigDir):
            self.logger.info('No configuration directory found, creating [{}]'.format(baseConfigDir))
            os.makedirs(baseConfigDir)

        if not os.path.isfile(Environment.configFilePath):
            self.logger.info(
                'No configuration file found, creating a new one in [{}].'
                .format(Environment.configFilePath)
            )
            with open(Environment.configFilePath, 'w+') as emptyFile:
                # The default minimal configuration
                emptyFile.write('{"server": {"fingerprint": "", "uri": "", "verifyCert": true}, "user": {"fingerprint": ""}}')

        with open(Environment.configFilePath, 'r+') as configFile:
            self.config = json.load(configFile)
            self.logger.debug('Configuration : [{}]'.format(self.config))

    def __saveConfig(self):
        with open(Environment.configFilePath, 'w+') as configFile:
            configFile.write(json.dumps(self.config, sort_keys=True, indent=4, separators=(',', ': ')))

    def server(self):
        return self.config['server']

    def user(self):
        return self.config['user']

    def persist(self):
        self.__saveConfig()
