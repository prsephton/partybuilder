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
from interfaces import (IOAuthDoneEvent, IOAuthPrincipal,
                        IOAuthSite, ITokenRequest)
from zope.authentication.interfaces import IUnauthenticatedPrincipal, IAuthentication
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import urlencode
from zope.schema.fieldproperty import FieldProperty
from datetime import datetime as dt
from oauthlib import oauth1

class OAuth2EditingPermission(grok.Permission):
    ''' A permission for editing OAuth2 apps list '''
    grok.name(u'OAuth2.editing')


class OAuthLogins(grok.ViewletManager):
    ''' embed with tal:context="structure provider:oauth2logins" '''
    grok.context(component.Interface)
    grok.require('zope.Public')


class OAuthDoneEvent(ObjectEvent):
    ''' An event that gets triggered after successful authorization '''
    grok.implements(IOAuthDoneEvent)


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


class V1AccessToken(grok.Model):
    grok.implements(ITokenRequest)
    parms = {}

    def __init__(self, client_key='',
                 client_secret='',
                 oauth_token='',
                 oauth_token_secret='',
                 verifier=''):
        self.parms = dict(client_key=client_key, client_secret=client_secret,
                          resource_owner_key=oauth_token,
                          resource_owner_secret=oauth_token_secret,
                          verifier=verifier)


class V1RequestToken(grok.Model):
    parms = {}
    req_token_uri = None
    auth_uri = None
    access = None
    grok.traversable('access')

    def __init__(self, req_token_uri, auth_uri,
                 consumer_key="", consumer_secret=""):
        super(V1RequestToken, self).__init__()
        self.req_token_uri = req_token_uri
        self.auth_uri = auth_uri
        self.parms = dict(client_key=consumer_key, client_secret=consumer_key)
        self.update_access()

    def client(self, request):
        self.parms['callback_uri'] = str(grok.url(request, self, name='@@access_token'))
        return oauth1.Client(**self.parms)

    def update_access(self, **kw):
        self.access = V1AccessToken(**kw)
        location.locate(self.access, self, 'access')

    def process(self, res):
        ''' Expect oauth_token, oauth_token_secret, oauth_callback_confirmed '''
        self.info = json.loads(res)
        kw = self.parms.copy()
        kw.update(self.info)
        self.update_access(**kw)


class V1RequestTokenView(grok.View):
    ''' Retrieve request token+secret, redirect browser to auth site. '''
    grok.context(V1RequestToken)
    grok.name('request_token')

    def render(self):
        client = self.context.client(self.request)
        uri, headers, body = client.sign(self.context.request_token_uri)

        req = Request(uri)
        for h, v in headers:
            req.add_header(h, v)
        req.add_data(body)
        res = urlopen(req).read()  # should be doing a post

        access = self.context.process(res)
#        Redirect with parameter: oauth_token (optional)
        data = dict(oauth_token=access.parms['oauth_token'])
        url = "{}?{}".format(self.context.auth_uri, urlencode(data))
        self.redirect(url)
        return '<a class="autolink" href="%s">Please visit: %s</a>' % (str(url), str(url))


class V1AccessView(grok.View):
    grok.context(V1RequestToken)
    grok.name('access_token')

    def render(self, **kw):
        access = self.context.access
        acecss.parms.update(kw)

        session = ISession(self.request)['OAuth2']
        session['info'] = access.info

        service = self.context.__parent__.service
        principal = component.queryAdapter(access, IOAuthPrincipal, name=service)
        session['principal'] = principal if principal else None

        grok.notify(OAuthDoneEvent(self.context.access))
        self.redirect(self.url(grok.getApplication()))


class V2Authorization(grok.Model):
    ''' An authorization request kicks off the oauth2 process. '''
    uri = ""
    parms = {}

    def __init__(self, uri, client_id="",
                 redirect_uri="", scope=u"",
                 state=""):
        self.uri=uri
        self.parms = dict(response_type = "code",
                          client_id = client_id,
                          redirect_uri = redirect_uri,
                          state = state)
        if type(scope) is not None and len(scope):
            self.parms['scope'] = scope

    def get_uri(self):
        parms = "&".join(["{}={}".format(k,v) for k,v in self.parms.items()])
        return  """{}?{}""".format(self.uri, parms)


class V2TokenRequest(grok.Model):
    ''' Represents a token exchange request. '''
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


class V2TokenView(ErrorView):
    ''' Once we have an auth code, we can issue a POST to the
        authorization server and exchange the code for a token.
        The token will be used in API requests until it expires,
        and we can use a refresh_token to refresh the token.
    '''
    grok.context(V2TokenRequest)
    grok.require('zope.Public')
    grok.name('tokenview')

    def update(self, code=None, state=None, **args):
        ''' Either code or error is defined here if this is in response to Authorization '''
        super(V2TokenView, self).update(**args)
        if code is not None:
            token = self.context.__parent__
            if token.state == state:
                self.context.code = code
                data = urlencode(self.context.parms)
                print "----------------------------------------------------"
                print "url=[%s]; data=[%s]" % (self.context.uri, data)
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
        else:
            self.error = 'Invalid code'
        if type(self.error) is str and len(self.error):
            print "-------------------------------------------------"
            print "Error [%s] in token exchange" % self.error


class IOAuth2App(component.Interface):
    ''' Defines fields needed for oauth2 app registration '''
    service = schema.Choice(title=u'Service: ',
                            description=u'The OAuth2 authenticator source',
                            vocabulary=u'oauth2.sources')
    authtype = schema.Choice(title=u'Type:', values=[u'OAuth-1', u'OAuth-2'], default=u'OAuth-2')
    icon = schema.Bytes(title=u'Display Icon:', required=False)
    auth_uri = schema.URI(title=u'Auth URI: ', required=False, description=u'Where to send the browser for authentication')
    token_uri = schema.URI(title=u'Token URI: ', required=False, description=u'Where to exchange auth token for request token')
    client_id = schema.TextLine(title=u'Client ID: ', required=False, description=u'Our Client/Consumer ID')
    secret = schema.TextLine(title=u'Secret: ', required=False, description=u'Our client secret if applicable')
    scope = schema.TextLine(title=u'Scope(s): ', required=False, description=u'List of services we will want to access')


class OAuth2App(grok.Model):
    ''' Represents an OAuth2 application instance '''
    grok.implements(IOAuth2App)
    service = FieldProperty(IOAuth2App['service'])
    authtype = FieldProperty(IOAuth2App['authtype'])
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

    def v1_authentication_uri(self, request):
        pass

    def authentication_uri(self, request):
        if self.authtype==u"OAuth-1":
            return self.v1_authentication_uri(request)

        self.state = str(randint(0, 1000))
        self.token = V2TokenRequest(self.token_uri,
                                    client_id=self.client_id,
                                    client_secret=self.secret)
        location.locate(self.token, self, 'token')

        # exchange the code for a token
        redirect_uri = str(grok.url(request, self.token, name="@@tokenview"))
        redirect_uri = redirect_uri.replace("http:", "https:")
        self.authorize = V2Authorization(self.auth_uri,
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
    ''' A form containing editable fields for oauth2 apps '''
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
    ''' A view to edit a registered oauth2 app. '''
    grok.context(OAuth2App)
    grok.name('edit')
    grok.require('OAuth2.editing')

    def render(self):
        sn = ISession(self.request)['OAuth2']
        sn['form'] = (self.context, 'oauth2appedit')
        self.redirect(self.url(self.context.__parent__.__parent__))


class OAuth2AppDelete(grok.EditForm):
    ''' A form to display confirming deletion '''
    grok.context(OAuth2App)
    grok.require('OAuth2.editing')

    form_fields = grok.Fields(IOAuth2App, for_display=True).select('service', 'client_id')

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
    ''' A view that deletes a registered OAuth2 app '''
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
    ''' A view that lists the set of defined oath2 login links  '''
    grok.context(OAuth2Applications)
    grok.name('index')
    grok.require('zope.Public')


class OAuth2ApplicationsEdit(grok.View):
    ''' A view to edit the list of oath2 applications '''
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


class OAuth2Viewlet(grok.Viewlet):
    ''' Installs an oauth2Applications folder if needed.
        Displays a list of clickable images or buttons which
        kick off the oauth2 authorization process.
    '''
    grok.context(component.Interface)  # Can be installed anywhere
    grok.viewletmanager(OAuthLogins)
    grok.require('zope.Public')

    def authenticated(self):
#        return False
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            return False
        return True

    def title(self):
        if self.authenticated():
            return self.request.principal.title

    def canEdit(self):
        if self.request.principal.id == 'zope.manager':
            return True
#        return True
        from zope.security import checkPermission
        return checkPermission('OAuth2.editing', grok.getSite())

    def logoutform(self):
        form = component.getMultiAdapter((self.context, self.request), name='logout')
        return form()

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

