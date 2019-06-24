import os

from requests.sessions import Session

from http.cookiejar import MozillaCookieJar

from requests_gpgauthlib import GPGAuthSession

from requests_gpgauthlib.utils import get_workdir

"""
Wraps the GPGAuthSession provided by the gpgauthlib package to allow
requests to be sent to the Passbolt instance with an incomplete certificate (verify=False)
"""
class GPGAuthSessionWrapper(GPGAuthSession):
    def __init__(self, gpg, server_url, user_fingerprint, verify, **kwargs):
        # Skip GPGAuthSession.__init__
        super(GPGAuthSession, self).__init__(**kwargs)

        self.server_url = server_url.rstrip('/')
        self.auth_uri = '/auth'

        self.gpg = gpg
        self.user_specified_fingerprint = user_fingerprint
        self.verify = verify

        self._cookie_filename = os.path.join(get_workdir(), 'gpgauth_session_cookies')
        self.cookies = MozillaCookieJar(self._cookie_filename)
        try:
            self.cookies.load(ignore_discard=True)
        except FileNotFoundError:
            pass
