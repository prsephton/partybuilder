'''
    Use the oauth2 protocol to identify principals.

    This can be used to implement "login via Google, Twitter, Facebook", etc.

    A set of login links (or pictures) can be produced here by simply including
    the OAuth2Logins viewlet manager. eg.

        tal:context="structure provider:oauth2logins"

    The details for each OAuth2 authentication service must be filled in by editing
    the list of "oauth2 applications".  These details are provided by registering a new
    application with the authorization source (eg. Google).

    To add new sources, define a new token adapter (see 'tokenadapters.py' for reference).

    This module expects to see a site implement the IOAuthSite interface, and an adapter
    defined which can provide the IOAuthPrincipalSource from the site.

    IOAuthPrincipalSource is a container for principals, and the interface requires
    new(id) and find(**kw) methods defined as per interfaces.py.  Because it is also
    an IPrincipalSource, the interface also requires the method: __contains__(self, id).

    IOAuthPrincipal is an extension of IPrincipal, and requires several additional fields
    that are used during token retrieval.  The retrieved token may be used in sunsequent
    API calls to the authenticated source.
'''
import grok
import simplejson as json
from zope import component, schema, location
from random import randint
from zope.component.interfaces import IObjectEvent, ObjectEvent
from zope.session.interfaces import ISession
from zope.authentication.interfaces import (IAuthentication, PrincipalLookupError,
                                            IPrincipalSource, IUnauthenticatedPrincipal,
                                            ILogoutSupported)
from zope.authentication.logout import LogoutSupported

from interfaces import (IOAuthDoneEvent, IOAuthPrincipal, IOAuthPrincipalSource,
                        IOAuthSite, ITokenRequest)
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import urlencode

class OAuth2EditingPermission(grok.Permission):
    ''' A permission for editing OAuth2 apps list '''
    grok.name(u'OAuth2.editing')

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


class TokenRequest(grok.Model):
    grok.implements(ITokenRequest)

    uri = ""
    parms = {}
    info = { "access_token": "",
             "token_type": None,
             "expires_in": 0,
             "refresh_token": None,
             "id_token": None,
             "access_type": "offline"
    }

    def __init__(self, uri, client_id="", client_secret=""):
        self.uri = uri
        grant_type = "authorization_code"
        self.parms = dict(grant_type=grant_type,
                          client_id=client_id,
                          client_secret=client_secret)

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


class OAuthDoneEvent(ObjectEvent):
    grok.implements(IOAuthDoneEvent)


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
            token = self.context.__parent__
            if token.state == state:
                self.context.code = code
                data = urlencode(self.context.parms)
#                 print "----------------------------------------------------"
#                 print "url=[%s]; data=[%s]" % (self.context.uri, data)
                req = Request(self.context.uri)
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
                req.add_data(data)
                res = urlopen(req).read()  # should be doing a post
                self.context.info = json.loads(res)
                # Update session information with auth info
                session = ISession(self.request)['OAuth2']
                session['info'] = self.context.info

                service = self.context.__parent__.service
                principal = component.queryAdapter(self.context, IOAuthPrincipal, name=service)
                session['principal'] = principal if principal else None

                # If we get here, we can notify subscribers.
                grok.notify(OAuthDoneEvent(self.context))

                self.redirect(self.url(grok.getApplication()))
            else:
                self.error = 'State Mismatch'


class IOAuthApp(component.Interface):
    service = schema.Choice(title=u'Service: ',
                            description=u'The OAuth2 authenticator source',
                            vocabulary=u'oauth2.sources')
    icon = schema.Bytes(title=u'Display Icon:', required=False)
    auth_uri = schema.URI(title=u'Auth URI: ')
    token_uri = schema.URI(title=u'Token URI: ')
    client_id = schema.TextLine(title=u'Client ID: ')
    secret = schema.TextLine(title=u'Secret: ')
    scope = schema.TextLine(title=u'Scope(s): ')


class OAuth2App(grok.Model):
    ''' Represents an OAuth2 application instance '''
    grok.implements(IOAuthApp)
    service = ""
    icon = None
    icon_filename = None
    auth_uri = ""
    token_uri = ""
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
        self.state = str(randint(0, 1000))
        self.token = TokenRequest(self.token_uri,
                                  client_id=self.client_id,
                                  client_secret=self.secret)
        location.locate(self.token, self, 'token')
        redirect_uri = str(grok.url(request, self.token, name="@@tokenview"))  # exchange code for token
        redirect_uri = redirect_uri.replace("http:", "https:")
        self.authorize = Authorization(self.auth_uri,
                                       redirect_uri=redirect_uri,
                                       client_id=self.client_id,
                                       scope=self.scope,
                                       state=self.state)
        location.locate(self.authorize, self, 'authorize')
        self.token.set_redirect_uri(redirect_uri)
        return self.authorize.get_uri()

    @property
    def apptoken(self):
        if self.token and 'token' in self.token.info:
            return token.info['token']


class OAuth2AppIconView(grok.View):
    ''' Returns an image if defined for the app '''
    grok.context(OAuth2App)
    grok.name('iconview')
    grok.require('zope.Public')

    def render(self):
        fn = self.context.icon_filename
        if type(fn) is str or type(fn) is unicode:
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
    grok.require('OAuth2.editing')

    def update(self):
        ''' record the icon file name here '''
        if 'form.icon' in self.request.form:
            icon = self.request.form['form.icon']
            if hasattr(icon, 'filename'):
                self.context.icon_filename = icon.filename

    def finish(self):
        sn = ISession(self.request)['OAuth2']
        sn['form'] = None
        self.redirect(self.request.URL)

    @grok.action(u'Apply')
    def apply(self, **data):
        self.applyData(self.context, **data)
        self.finish()

    @grok.action("Cancel", validator=lambda *a, **k: {})
    def cancel(self, **data):
        self.finish()


class AppEdit(grok.View):
    grok.context(OAuth2App)
    grok.name('edit')
    grok.require('OAuth2.editing')

    def render(self):
        sn = ISession(self.request)['OAuth2']
        sn['form'] = (self.context, 'oauth2appedit')
        self.redirect(self.url(self.context.__parent__.__parent__))


class OAuth2AppDelete(grok.EditForm):
    grok.context(OAuth2App)
    grok.require('OAuth2.editing')

    form_fields = grok.Fields(IOAuthApp, for_display=True).select('service', 'client_id')

    def finish(self):
        sn = ISession(self.request)['OAuth2']
        sn['form'] = None
        self.redirect(self.request.URL)

    @grok.action("Delete this app")
    def delete(self, **data):
        ct =  self.context.__parent__
        app_id = self.context.app_id
        del ct[app_id]
        self.finish()

    @grok.action("Cancel", validator=lambda *a, **k: {})
    def cancel(self, **data):
        self.finish()


class AppDelete(grok.View):
    grok.context(OAuth2App)
    grok.name('delete')
    grok.require('OAuth2.editing')

    def render(self):
        sn = ISession(self.request)['OAuth2']
        sn['form'] = (self.context, 'oauth2appdelete')
        self.redirect(self.url(self.context.__parent__.__parent__))


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
        return self[app_id]


class OAuth2ApplicationsView(grok.View):
    grok.context(OAuth2Applications)
    grok.name('index')
    grok.require('zope.Public')

    def canEdit(self):
#        return True
        from zope.security import checkPermission
        return checkPermission('OAuth2.editing', grok.getSite())


class OAuth2ApplicationsEdit(grok.View):
    grok.context(OAuth2Applications)
    grok.name('edit')
    grok.require('OAuth2.editing')

    form = None

    def update(self):
        self.form = None
        sn = ISession(self.request)['OAuth2']
        if sn is not None and 'form' in sn.keys():
            if sn['form']:
                ctx, view = sn['form']
                self.form = component.queryMultiAdapter((ctx, self.request), name=view)


class OAuth2AppNew(grok.View):
    ''' Create a new OAuth2 application and edit it '''
    grok.context(OAuth2Applications)
    grok.name('new')
    grok.require('OAuth2.editing')

    def render(self):
        self.redirect(self.url(self.context.new(), 'edit'))

class OAuth2Authenticate(grok.LocalUtility):
    grok.implements(IAuthentication)
    grok.site(IOAuthSite)

    def authenticate(self, request):
        ''' We are already authenticated if the session contains a principal. '''
        print 'authenticate called'
        sn = ISession(request)['OAuth2']
        if 'principal' in sn.keys():
            return sn['principal']

    def unauthenticatedPrincipal(self):
        pass

    def unauthorized(self, id, request):
        ''' Remove the session item to force re-authentication '''
        sn = ISession(request)['OAuth2']
        if 'principal' in sn.keys():
            del sn['principal']

    def getPrincipal(self, id):
        print 'getprincipal called: %s' % id
        source = IOAuthPrincipalSource(grok.getSite())
        principal = source.find(id=id)
        if len(principal)==1:
            return principal[0]
        raise PrincipalLookupError(id)

class AuthLogoutSupported(grok.Adapter):
    grok.context(OAuth2Authenticate)
    grok.implements(ILogoutSupported)

    def __new__(self, context):
        return LogoutSupported()


class InstallAuth(grok.View):
    ''' A view to install or remove the local authentication utility '''
    grok.context(IOAuthSite)
    grok.require('OAuth2.editing')

    def render(self, uninstall=False):
        site = grok.getSite()
        sm = site.getSiteManager()
        name = 'OpenAuth2'
        print "%s" % [k for k in sm.keys()]
        if uninstall and name in sm.keys():
            util = sm[name]
            sm.unregisterUtility(component=util, provided=IAuthentication)
            del sm[name]
        elif name not in sm.keys():
           obj = sm[name] = OAuth2Authenticate()
           sm.registerUtility(component=obj, provided=IAuthentication)
           print 'installed'
        self.redirect(self.url(self.context))


class BaLogout(grok.View):
    ''' A 'basic_auth' logout '''
    grok.context(component.Interface)
    grok.require('zope.Public')

    def render(self):
        self.request.response.setStatus('Unauthorized')   # challenges (logs out) basic auth
        self.request.response.setHeader('WWW-Authenticate', 'basic realm="Zope"', 1)
        self.message="You have been logged out"
        return self.message


class OAuth2Viewlet(grok.Viewlet):
    ''' Installs an oauth2Applications folder if needed.
        Displays a list of clickable images or buttons which
        kick off the oauth2 authorization process.
    '''
    grok.context(component.Interface)  # Can be installed anywhere
    grok.viewletmanager(OAuth2Logins)
    grok.require('zope.Public')

    def authenticated(self):
        return False
#         if IUnauthenticatedPrincipal.providedBy(self.request.principal):
#             return False
#         return True

    def title(self):
        if self.authenticated:
            return self.request.principal.title

    def update(self):
        app = grok.getApplication()
        if 'oauth2Applications' in app.keys():
            self.oauth = app['oauth2Applications']
        else:
            self.oauth = app['oauth2Applications'] = OAuth2Applications()
        if 'oauth2editing' in self.request:
            try:
                self.oauth.editmode = int(self.request['oauth2editing'])
            except:
                pass

