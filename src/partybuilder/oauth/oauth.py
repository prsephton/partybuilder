import grok
import simplejson as json
from six.moves.urllib.parse import urljoin, urlopen, urlencode
from zope import component, schema

class ErrorView(grok.View):
    grok.context(component.Interface)
    grok.require('zope.Public')
    grok.baseclass()

    error = None
    error_description = None
    error_uri = None

    def update(self, error=None,
               error_description=None,
               error_uri=None):
        if error is not None:
            self.error = error
            self.error_description = error_description
            self.error_uri = error_uri


class Authorization(grok.Model):
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
    grok.context(Authorization)
    grok.require('zope.Public')

    def render(self):   # Get an access code
        self.redirect(self.context.get_uri())


class TokenRequest(grok.Model):
    uri = ""
    parms = {}
    info = { "access_token": "",
             "token_type": None,
             "expires_in": 0,
             "refresh_token": None,
             "id_token": None
    }

    def __init__(self, uri, redirect_uri="", client_id="", secret=""):
        grant_type = "authorization_code"
        self.parms = dict(grant_type=grant_type,
                          redirect_uri=redirect_uri,
                          client_id=client_id,
                          secret=secret)

    @property
    def code(self):
        if 'code' in self.parms: return self.parms['code']
    @code.setter
    def code(self, code):
        self.parms['code'] = code

    def get_uri(self):
        parms = "&".join(["{}={}".format(k,v) for k,v in self.parms])
        return  """{}?{}""".format(self.uri, parms)


class TokenView(ErrorView):
    grok.context(TokenRequest)
    grok.require('zope.Public')

    def update(self, code=None, state=None, **args):
        ''' Either code or error is defined here if this is in response to Authorization '''
        super(TokenView, self).update(**args)
        if code is not None:
            if self.context.state == state:
                self.context.code = code
                data = urlencode(self.context.parms)
                res = urlopen(self.context.url, data=data).read()  # should be doing a post
                self.context.info = json.loads(res)
            else:
                self.error = 'State Mismatch'

class OAuth2App(grok.Model):
    ''' Represents an OAuth2 application instance '''
    description = ""
    uri = ""
    client_id = None
    secret = None
    scope = None
    token = None
    grok.traversable('token')

    def __init__(self, uri, client_id, secret, scope, description=""):
        self.uri = uri
        self.client_id = client_id
        self.secret = secret
        self.scope = scope
        self.description = description
        self.state = ""

    def authenticate(self):
        from random import randint
        self.state = str(randint(1000))
        redirect_uri = grok.url(self, "oauth2view")         # Error handling
        self.token = TokenRequest(self.uri,
                                     redirect_uri=redirect_uri,
                                     client_id=self.client_id,
                                     secret=self.secret)
        redirect_uri = grok.url(self.token, "tokenview")  # exchange code for token
        self.auth = Authorization(self.uri,
                                  redirect_uri=redirect_uri,
                                  client_id=self.client_id,
                                  scope=self.scope,
                                  state=self.state)

class OAuth2View(ErrorView):
    grok.context(OAuth2App)

