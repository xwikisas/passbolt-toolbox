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
        self.resourceURI = resource['uri']
        self.resourceUsername = resource['username']
        self.oldPassword = oldPassword
        self.newPassword = newPassword

    """
    Update the password on its related service. Should return True if the update succeeds, otherwise False
    """
    def updatePassword():
        raise NotImplementedError("Please implement this method")
