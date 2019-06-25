"""
Parent class for defining connectors, those connectors are in charge of updating the password
of a specific service using the information they get at initialization.
"""


class Connector:
    """
    @param resource : information about the resource to update (server url, description, username, ...)
    @param oldPassword : the old resource password
    @param newPasword : the new resource password
    """
    def __init__(self, resource, oldPassword, newPassword):
        self.resource = resource
        self.resourceURI = resource['Resource']['uri']
        self.resourceUsername = resource['Resource']['username']
        self.oldPassword = oldPassword
        self.newPassword = newPassword

    """
    Update the password on its related service. Should return True if the update succeeds, otherwise False
    """
    def updatePassword(self):
        raise NotImplementedError("Please implement this method")

    """
    Rollback the previously updated password. Should return True if the rollback succeeded, otherwise False.
    This method will always be called after #updatePassword(), thus it can take advantage of connector attributes
    created during the first call.
    """
    def rollbackPasswordUpdate(self):
        raise NotImplementedError("Please implement this method")
