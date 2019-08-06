import logging


# Manages the local keyring
class KeyringManager:
    logger = logging.getLogger('KeyringManager')

    def __init__(self, keyring):
        self.keyring = keyring

        # Use to manage which keys are part of the local keyring
        self.addedKeysCache = []
        # Get the keys currently in the keyring
        self.keysInKeyring = [x['keyid'][-8:] for x in self.keyring.list_keys()]

    def maybeImportKey(self, armoredKey, keyID, firstName, lastName):
        if (keyID not in self.keysInKeyring
                and keyID not in self.addedKeysCache):
            self.logger.info('Importing missing public key for {} {} ({})'
                             .format(firstName, lastName, keyID))
            importResult = self.keyring.import_keys(armoredKey)
            if importResult:
                self.addedKeysCache.append(keyID)
            else:
                self.logger.error('Failed to import key [{}] in the keyring'.format(keyID))
                # TODO : Do something, throw an error ?

    def maybeImportUser(self, user):
        self.maybeImportKey(user['Gpgkey']['armored_key'],
                            user['Gpgkey']['key_id'],
                            user['Profile']['first_name'],
                            user['Profile']['last_name'])

    # Make sure that the given Users are present in the local keyring
    def maybeImportGroupUsers(self, groupUsers):
        for groupUser in groupUsers:
            self.maybeImportKey(groupUser['User']['Gpgkey']['armored_key'],
                                groupUser['User']['Gpgkey']['key_id'],
                                groupUser['User']['Profile']['first_name'],
                                groupUser['User']['Profile']['last_name'])
