''' Implements a simple login view that maps to any context.
'''
import grok
from zope import component, schema
from zope.authentication.logout import ILogout, ILogoutSupported
from zope.session.interfaces import ISession
from interfaces import IOAuthPrincipalSource
from zope.password.interfaces import IPasswordManager
from zope.schema.fieldproperty import FieldProperty
from zope.authentication.interfaces import IAuthentication, ILogoutSupported
from zope.component._api import queryAdapter

class ILoginFields(component.Interface):
    login = schema.TextLine(title=u'Login: ')
    secret = schema.Password(title=u'Password: ')


class Login(grok.Model):
    grok.implements(ILoginFields)
    login = FieldProperty(ILoginFields['login'])
    secret = FieldProperty(ILoginFields['secret'])


class LoginView(grok.Form):
    ''' A password based login vies '''
    grok.context(component.Interface)
    grok.name('login')
    form_fields = grok.Fields(ILoginFields)    
    
    @grok.action(u"OK")
    def do_login(self, **data):
        login = Login()
        self.applyData(login, **data)
        principals = IOAuthPrincipalSource(grok.getApplication())
        account = principals.find(login=login.login, domain=principals.domain)
        if account:  # check password, and authenticate if match
            from zope.password.password import SSHAPasswordManager
            mgr = SSHAPasswordManager()
            if mgr.checkPassword(account.secret, login.secret):
                session = ISession(self.request)['OAuth2']
                session['principal'] = account   # Found the principal


    @grok.action(u"Cancel", validator=lambda *a, **k: {})
    def cancel(self, **data):
        pass


class Logout(grok.Form):
    ''' A logout form for ordinary authentication utilities '''
    grok.context(component.Interface)
    grok.require('zope.Public')

    @grok.action(u'Logout')
    def logout(self):
        site = grok.getSite()
        if not queryAdapter(site, ILogoutSupported):
            self.redirect(self,url(self.context, '@@balogout'))
        sm = site.getSiteManager()
        auth = sm.getUtility(IAuthentication)
        ILogout(auth).logout(self.request)
        self.redirect(self.request.URL)


class BaLogout(grok.View):
    ''' A 'basic_auth' logout '''
    grok.context(component.Interface)
    grok.require('zope.Public')

    def render(self):
        self.request.response.setStatus('Unauthorized')   # challenges (logs out) basic auth
        self.request.response.setHeader('WWW-Authenticate', 'basic realm="Zope"', 1)
        self.message="You have been logged out"
        return self.message


