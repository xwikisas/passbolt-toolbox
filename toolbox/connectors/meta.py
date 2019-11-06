"""
Error thrown when a password fails to be updated in a service.
"""
class PasswordUpdateError(Exception):
    pass

"""
Parent class for defining connectors, those connectors are in charge of updating the password
of a specific service using the information they get at initialization.
"""
class Connector:
    """
    @param configManager : the configuration manager
    @param resource : the resource object itself
    @param oldPassword : the old resource password
    @param newPasword : the new resource password
    """
    def __init__(self, configManager, resource, oldPassword, newPassword):
        self.configManager = configManager
        self.resource = resource
        self.resourceURI = resource['Resource']['uri']
        self.resourceUsername = resource['Resource']['username']
        self.oldPassword = oldPassword
        self.newPassword = newPassword

    """
    Update the password on its related service.

    @throws PasswordUpdateError if the update failed
    """
    def updatePassword(self):
        raise NotImplementedError("Please implement this method")

    """
    Rollback the previously updated password.
    This method will always be called after #updatePassword(), thus it can take advantage of connector attributes
    created during the first call.

    @throws PasswordUpdateError if the update failed
    """
    def rollbackPasswordUpdate(self):
        raise NotImplementedError("Please implement this method")
