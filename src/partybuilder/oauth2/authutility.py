import grok
from zope.authentication.logout import LogoutSupported, ILogout
from zope.authentication.interfaces import (IUnauthenticatedPrincipal, ILogoutSupported,
                                            IAuthentication, PrincipalLookupError,
                                            IPrincipalSource)
from interfaces import (IOAuthPrincipalSource, IOAuthSite)
from zope.session.interfaces import ISession

class UnauthenticatedPrincipal(object):
    grok.implements(IUnauthenticatedPrincipal)
    id = u''
    title = u'Unauthenticated'
    description = u'An Unauthenicated Principal'


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
        return UnauthenticatedPrincipal()

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


class Logout(grok.Adapter):
    """An adapter for IAuthentication utilities that don't implement ILogout."""

    grok.context(OAuth2Authenticate)
    grok.implements(ILogout)

    def __init__(self, auth):
        self.auth = auth

    def logout(self, request):
        self.auth.unauthorized(None, request)

        
class AuthLogoutSupported(grok.Adapter):
    ''' An adapter that says our authentication utility supports logout '''
    grok.context(OAuth2Authenticate)
    grok.implements(ILogoutSupported)

    def __new__(self, context):
        return LogoutSupported(context)


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


