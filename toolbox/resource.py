from datetime import datetime
import logging
import re

"""
Wraps a resource JSON as returned by the Passbolt server to add specific methods.
This is especially useful when dealing with resource metadata that we store as part of the description of the resource
and that are thus not directly accessible.
"""
class Resource:
    logger = logging.getLogger('Resource')
    lastUpdatePropertyPattern = re.compile('^>>> Last password update : (\d{2}\/\d{2}\/\d{4})$')
    updateCountPropertyPattern = re.compile('^>>> Update count : (\d*)$')
    connectorTypePropertyPattern = re.compile('^>>> Connector : (.*)$')
    dateFormat = "%d/%m/%Y"

    def __init__(self, resourceJSON):
        self.resourceJSON = resourceJSON
        self.lastUpdateDate = None
        self.updateCount = 0
        self.connectorType = 'XWiki'
        self.__parseResourceDescription()

    """
    Allow direct access to the JSON content when needed
    """
    def __getitem__(self, key):
        return self.resourceJSON[key]

    def __parseResourceDescription(self):
        lines = self.resourceJSON['Resource']['description'].split('\n')

        self.cleanDescription = []
        for line in lines:
            updateDateMatch = self.lastUpdatePropertyPattern.match(line)
            if updateDateMatch is not None:
                self.lastUpdateDate = datetime.strptime(updateDateMatch.group(1), self.dateFormat)
            else:
                updateCountMatch = self.updateCountPropertyPattern.match(line)
                if updateCountMatch is not None:
                    self.updateCount = int(updateCountMatch.group(1))
                else:
                    connectorTypeMatch = self.connectorTypePropertyPattern.match(line)
                    if connectorTypeMatch is not None:
                        self.connectorType = connectorTypeMatch.group(1)

            # We keep lines that are not related to the renewer
            if (updateDateMatch is None
                and updateCountMatch is None
                and connectorTypeMatch is None):
                self.cleanDescription.append(line)

        self.logger.debug('Last update date : [{}]'.format(self.lastUpdateDate))
        self.logger.debug('Update count : [{}]'.format(self.updateCount))
        self.logger.debug('Connector type : [{}]'.format(self.connectorType))
        self.logger.debug('Resulting description : [{}]'.format(self.cleanDescription))

    """
    Registers that the resource has been updated, thus updating the description of the resouce
    for its last update date and its update count.
    """
    def markAsUpdated(self):
        self.updateCount = self.updateCount + 1
        self.lastUpdateDate = datetime.now()

    def generateDescription(self):
        finalDescription = self.cleanDescription.copy()
        finalDescription.append('>>> Last password update : {}'.format(self.lastUpdateDate.strftime(self.dateFormat)))
        finalDescription.append('>>> Update count : {}'.format(self.updateCount))
        finalDescription.append('>>> Connector : {}'.format(self.connectorType))
        return '\n'.join(finalDescription)
