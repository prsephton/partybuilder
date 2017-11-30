import grok
import simplejson as json
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode
from zope import component, schema
from random import randint


class OAuth2Logins(grok.ViewletManager):
    ''' embed with tal:context="structure provider:oauth2logins" '''
    grok.context(component.Interface)
    grok.require('zope.Public')


class ErrorView(grok.View):
    ''' An error display which serves as a base for redirect_urls '''
    grok.context(component.Interface)
    grok.require('zope.Public')
    grok.template('errorview')
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
    ''' An authorization request kicks off the oauth2 process. '''
    uri = ""
    parms = {}

    def __init__(self, uri, client_id="",
                 redirect_uri="", scope="",
                 state=""):
        self.uri=uri
        self.parms = dict(response_type = "code",
                          client_id = client_id,
                          redirect_uri = redirect_uri,
                          scope = scope,
                          state = state)

    def get_uri(self):
        parms = "&".join(["{}={}".format(k,v) for k,v in self.parms.items()])
        return  """{}?{}""".format(self.uri, parms)


class AuthView(grok.View):
    ''' This view simply redirects to the authorization uri '''
    grok.context(Authorization)
    grok.require('zope.Public')
    grok.name('index')

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

    def __init__(self, uri, client_id="", secret=""):
        grant_type = "authorization_code"
        self.parms = dict(grant_type=grant_type,
                          client_id=client_id,
                          secret=secret)

    def set_redirect_uri(self, uri):
        self.parms['redirect_uri'] = uri
        self._p_changed = True

    @property
    def code(self):
        if 'code' in self.parms: return self.parms['code']
    @code.setter
    def code(self, code):
        self.parms['code'] = code
        self._p_changed = True


class TokenView(ErrorView):
    ''' Once we have an auth code, we can issue a POST to the
        authorization server and exchange the code for a token.
        The token will be used in API requests until it expires,
        and we can use a refresh_token to refresh the token.
    '''
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


class IOAuthApp(component.Interface):
    service = schema.TextLine(title=u'Service: ')
    icon = schema.Bytes(title=u'Display Icon:')
    uri = schema.URI(title=u'URI: ')
    client_id = schema.TextLine(title=u'Client ID: ')
    secret = schema.TextLine(title=u'Secret: ')
    scope = schema.TextLine(title=u'Scope(s): ')


class OAuth2App(grok.Model):
    ''' Represents an OAuth2 application instance '''
    grok.implements(IOAuthApp)
    service = ""
    icon = None
    icon_filename = None
    uri = ""
    client_id = None
    secret = None
    scope = None
    token = None
    authorize = None
    grok.traversable('token')
    grok.traversable('authorize')

    def __init__(self, app_id):
        self.app_id = app_id

    def authentication_uri(self, request):
        self.state = str(randint(1000))
        self.token = TokenRequest(self.uri,
                                  client_id=self.client_id,
                                  secret=self.secret)
        redirect_uri = grok.url(request, self.token, "tokenview")  # exchange code for token
        self.authorize = Authorization(self.uri,
                                       redirect_uri=redirect_uri,
                                       client_id=self.client_id,
                                       scope=self.scope,
                                       state=self.state)
        self.token.set_redirect_uri(redirect_uri)
        return grok.url(request, self.authorize)

    @property
    def apptoken(self):
        if self.token and 'token' in self.token.info:
            return token.info['token']


class OAuth2AppIconView(grok.View):
    ''' Returns an image if defined for the app '''
    grok.context(OAuth2App)
    grok.name('icon')
    grok.require('zope.Public')

    def render(self):
        fn = self.context.icon_filename
        if type(fn) is str:
            fn = fn.lower()
            if fn.find('.gif')>0:
                mimetype="image/gif"
            elif fn.find('.png')>0:
                mimetype="image/png"
            elif fn.find('.svg')>0:
                mimetype="image/svg+xml"
            elif fn.find('.jpg')>0 or fn.find('jpeg')>0:
                mimetype="image/jpeg"
            self.response.setHeader('Content-Type', mimetype)
            disposition = "inline; filename='{}'".format(fn)
            self.response.setHeader("Content-Disposition", disposition)
            return self.context.icon
        return ""


class OAuth2AppEdit(grok.EditForm):
    grok.context(OAuth2App)
    grok.name('edit')
    grok.require('zope.Public')

    def update(self):
        ''' record the icon file name here '''
        if 'form.icon' in self.request.form:
            icon = self.request.form['form.icon']
            self.context.icon_filename = icon.filename


class OAuth2AppEdit(grok.EditForm):
    grok.context(OAuth2App)
    grok.name('delete')
    grok.require('zope.Public')
    form_fields = grok.Fields(IOAuthApp, for_display=True).select('service', 'client_id')

    @grok.action("Delete this app")
    def delete(self, **data):
        ct =  self.context.__parent__
        app_id = self.context.app_id
        del ct[app_id]

    @grok.action("Cancel")
    def cancel(self, **data):
        self.redirect(self.url(self.__parent__, 'edit'))


#_______________________________________________________________________
#  Rendering OAuth2Viewlet inside an application view will add an
#  instance of OAuth2Applicatons to the application container.
#  The viewlet will render an area containing either buttons or icons
#  which allow authentication via the associated service.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~`
class OAuth2Applications(grok.Container):
    ''' A container for OAuth2 applications '''
    editmode = False

    def __init__(self):
        super(OAuth2Applications, self).__init__()
        self.sequence = 0

    def new(self):
        app_id = str(self.sequence)
        self[app_id] = OAuth2App(app_id)
        self.sequence += 1


class OAuth2ApplicationsView(grok.View):
    grok.context(OAuth2Applications)
    grok.name('index')
    grok.require('zope.Public')

    def update(self, oauth2editing=False):
        self.context.editmode = oauth2editing


class OAuth2ApplicationsEdit(grok.View):
    grok.context(OAuth2Applications)
    grok.name('edit')
    grok.require('zope.Public')

    def update(self, oauth2editing=True):
        self.context.editmode = oauth2editing


class OAuth2AppNew(grok.View):
    ''' Create a new OAuth2 application and edit it '''
    grok.context(OAuth2Applications)
    grok.name('new')
    grok.require('zope.Public')

    def render(self):
        self.redirect(self.url(self.context.new(), 'edit'))


class OAuth2Viewlet(grok.Viewlet):
    ''' Installs an oauth2Applications folder if needed.
        Displays a list of clickable images or buttons which
        kick off the oauth2 authorization process.
    '''
    grok.context(component.Interface)  # Can be installed anywhere
    grok.viewletmanager(OAuth2Logins)
    grok.require('zope.Public')

    def update(self):
        app = grok.getApplication()
        if 'oauth2Applications' in app.keys():
            self.oauth = app['oauth2Applications']
        else:
            self.oauth = app['oauth2Applications'] = OAuth2Applications()

