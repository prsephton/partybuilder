import grok
import simplejson as json
from six.moves.urllib.parse import urljoin
from six.moves.urllib.error import HTTPError
from six.moves.urllib.request import urlopen

class authorization(grok.Model):
    uri = ""
    parms = {}

    def __init__(self, uri, client_id="",
                 redirect_uri="", scope="", state=""):
        self.uri=uri
        self.parms = dict(response_type = "code",
                          client_id = client_id,
                          redirect_uri = redirect_uri,
                          scope = scope,
                          state = state)

    def get_uri(self):
        parms = "&".join(["{}={}".format(k,v) for k,v in self.parms])
        return  """{}?{}""".format(self.uri, parms)


class AuthView(grok.View):
    grok.context(authorization)
    grok.require('zope.Public')

    def render(self):
        self.redirect(self.context.get_uri())


class TokenRequest(grok.Model):
    uri = ""
    parms = {}

    def __init__(self, uri, grant_type="", code="", redirect_uri="", client_id=""):
        self.parms = dict(grant_type=grant_type,
                          code=code,
                          redirect_uri=redirect_uri,
                          client_id=client_id)

    def get_uri(self):
        parms = "&".join(["{}={}".format(k,v) for k,v in self.parms])
        return  """{}?{}""".format(self.uri, parms)

class TokenView(grok.View):
    grok.context(TokenRequest)
    grok.require('zope.Public')

    def update(self, code=None, state=None, error=None,
               error_description=None, error_uri=None):
        ''' Either code or error is defined here if this is in response to Authorization '''

    def render(self):
        pass