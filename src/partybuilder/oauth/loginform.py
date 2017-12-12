''' Implements a simple login view that maps to any context.
'''
import grok
from zope import component, schema
from zope.session.interfaces import ISession
from interfaces import IOAuthPrincipalSource
from zope.password.interfaces import IPasswordManager
from zope.schema.fieldproperty import FieldProperty


class ILoginFields(component.Interface):
    login = schema.TextLine(title=u'Login: ')
    secret = schema.Password(title=u'Password: ')


class Login(grok.Model):
    grok.implements(ILoginFields)
    login = FieldProperty(ILoginFields['login'])
    secret = FieldProperty(ILoginFields['secret'])


class LoginView(grok.Form):
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


