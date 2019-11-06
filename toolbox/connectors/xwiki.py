import logging
import requests

from html.parser import HTMLParser
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from urllib.parse import urlparse

from .meta import Connector
from .meta import PasswordUpdateError


class XWikiHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'html':
            for attr in attrs:
                if attr[0] == 'data-xwiki-rest-url':
                    self.foundRESTURL = attr[1]

    def feed(self, data):
        self.foundRESTURL = ''
        super(XWikiHTMLParser, self).feed(data)
        return self.foundRESTURL


class XWikiConnector(Connector):
    logger = logging.getLogger('XWikiConnector')
    parser = XWikiHTMLParser()
    headers = {
        'Content-Type': 'text/plain',
        'Accept': 'application/json'
    }

    def __sendPasswordUpdateRequest(self, oldPassword, newPassword):
        try:
            result = requests.put(
                '{}/wikis/xwiki/spaces/XWiki/pages/{}/objects/XWiki.XWikiUsers/0/properties/password'
                .format(self.restRootURL, self.resourceUsername),
                data=newPassword,
                auth=HTTPBasicAuth(self.resourceUsername, oldPassword),
                verify=False,
                headers=self.headers)
            self.logger.debug('Server response : [{}]'.format(result.content))

            if result.status_code != 202:
                raise PasswordUpdateError('Server returned an invalid status code : [{}]'.format(result.status_code))
        except RequestException as e:
            raise PasswordUpdateError('Communication with the XWiki server failed : [{}]'.format(e))

    def updatePassword(self):
        self.resourceUsername = self.resource['Resource']['username']
        self.logger.debug('Resource username : [{}]'.format(self.resourceUsername))

        try:
            # First step, try to reach the instance using the link provided
            result = requests.get(self.resource['Resource']['uri'], verify=False)
            # Find the REST URL given in the page we are dealing with
            # Here we'll make the assumption that the REST endpoint of XWiki will always end with "/rest"
            # thus, we can have :
            # mywiki.org/rest
            # mywiki.org/xwiki/rest
            # ... which covers most of the use cases
            restRawPath = self.parser.feed(result.content.decode('utf-8'))
            if restRawPath == '' or restRawPath is None:
                raise PasswordUpdateError('Failed to get the REST API path for the XWiki server')

            restRootPath = restRawPath.split('rest')[0] + 'rest'
            parsedURL = urlparse(self.resource['Resource']['uri'])
            # Compute the protocol + host part of the url
            baseURL = '{}://{}'.format(parsedURL.scheme, parsedURL.netloc)

            # Store the root URL in case we need it in #rollbackPasswordUpdate()
            self.restRootURL = baseURL + restRootPath

            return self.__sendPasswordUpdateRequest(self.oldPassword, self.newPassword)
        except RequestException as e:
            raise PasswordUpdateError('Communication with the XWiki server failed : [{}]'.format(e))

    def rollbackPasswordUpdate(self):
        return self.__sendPasswordUpdateRequest(self.newPassword, self.oldPassword)
