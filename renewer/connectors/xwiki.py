from .meta import Connector

class XWikiConnector(Connector):
    def updatePassword(self):
        # XXX
        return True
        result = requests.put(
            '{}/rest/wikis/xwiki/spaces/XWiki/pages/{}/objects/XWiki.XWikiUsers/0/properties/password'
            .format(resourceURI, resourceUsername),
            data=newPassword,
            auth=HTTPBasicAuth(resourceUsername, oldPassword))

        return result.status_code == 202

