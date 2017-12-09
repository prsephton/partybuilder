''' Serve up OAuth2 authorization for our own site.
'''
import grok, hashlib, os
from zope import component, schema
from zope.session.interfaces import ISession
from zope.schema.fieldproperty import FieldProperty
from six.moves.urllib.parse import urlencode
from datetime import datetime as dt
from datetime import timedelta as td


class IUserApplication(component.Interface):
    '''   An application registered by an existing user
    '''
    userid = schema.TextLine(title=u'Internal User ID: ')
    appname = schema.TextLine(title=u'Application Name: ')
    redirect = schema.URI(title=u'Redirect URI: ')
    client_id = schema.TextLine(title=u'Client ID: ')
    secret = schema.TextLine(title=u'Secret: ')


class IUserGrant(component.Interface):
    ''' A user grant associated with a specific client_id.
    '''
    access_token = schema.TextLine(title=u'Access Token: ')
    refresh_token = schema.TextLine(title=u'Refresh Token: ')
    auth_token = schema.TextLine(title=u'Authorization Token: ')
    expires_after = schema.Datetime(title=u'Expires: ')
    scope = schema.TextLine(title=u'Scope(s): ')
    offline_ok = schema.Bool(title=u'Offline OK: ', default=False)


class UserApplication(grok.Container):
    ''' Carries the information which defines a specific user application. 
        An application may contain numerous grants
    '''
    grok.implements(IUserApplication)
    userid = FieldProperty(IUserApplication['userid'])
    appname = FieldProperty(IUserApplication['appname'])
    redirect = FieldProperty(IUserApplication['redirect'])
    client_id = FieldProperty(IUserApplication['client_id'])
    secret = FieldProperty(IUserApplication['secret'])


class UserApplications(grok.Container):
    ''' Contains registered OAuth2 applications with client ID as keys. 
        One registered user may have numerous applications defined
    '''
    seq = 0

    def gen_client_id(self):
        l_id = "{}.{}".format(self.seq, os.urandom(1024))
        self.seq += 1
        return hashlib.sha256(l_id).hexdigest()


class AuthView(grok.View):
    ''' A view which we can access that returns a unique authorization code.
        We redirect to the redirect_uri if supplied, passing the code.
        If the redirect_uri was not supplied, we redirect to our JSON API
        to return the code.
    '''
    grok.require('zope.Public')
    grok.context(UserApplications)

    def render(self, redirect_uri=None, state=None, response_type = "code",
               client_id = None, scope = None):
        if client_id is None:
            pass
        if scope is None:
            pass
        if response_type != 'code':
            pass
        if client_id in self.context.keys():
            code = hashlib.sha256(os.urandom(1024)).hexdigest()
            session = ISession(self.request)['oauth2serve']
            session = session['client_id']
            session['redirect_uri'] = redirect_uri
            session['state'] = state
            session['code'] = code
            session['issued'] = dt.now()
            data = dict(state=state, code=code)
            if redirect_uri is not None:
                uri = "{}?{}".format(redirect_uri, urlencode(data))
                self.redirect(uri)
            else:
                self.redirect(self.url(self.context, name='as_json', data=data))
        else:
            pass


class OAuth2API(grok.JSON):
    ''' The JSON part of the API '''
    grok.context(UserApplications)

    def as_json(self, **kw):
        return kw

    def token(self, code=None, redirect_uri=None, client_id=None,
              client_secret=None, scope=None, grant_type=None):

        if grant_type!='authorization_code':
            return {}
        if client_id not in self.context.keys():
            return {}
        session = ISession(self.request)['oauth2serve']
        if 'client_id' not in self.context.keys():
            return {}
        if 'client_id' not in self.session:
            return {}

        session = session['client_id']
        if session['redirect_uri'] != redirect_uri:
            return {}
        if session['code'] != code:
            return {}
        if session['scope'] != scope:
            return {}
        who = self.context['client_id']
        if who.secret != client_secret:
            return {}

        who.access_token = hashlib.sha256(os.urandom(1024)).hexdigest()
        who.refresh_token = hashlib.sha256(os.urandom(1024)).hexdigest()
        id_token = {}

#        id_token = json.dumps()

        return dict(token_type="Bearer",
                    access_token=who.access_token,
                    refresh_token=who.refresh_token,
                    expires_in=3600,
                    id_token=id_token)
