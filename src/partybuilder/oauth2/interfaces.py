from zope import component, schema
from zope.security.interfaces import IPrincipal
from zope.authentication.interfaces import IPrincipalSource

class IOAuthenticatedEvent(component.interfaces.IObjectEvent):
    ''' This event is fired when OpenAuth2 returns a request token.
        The object which is the subject of the event is an instance 
        of the user who has been authenticated
        We can use @grok.subscribe(IOAuthenticatedEvent) to subscribe
    '''

class IOAuthSite(component.Interface):
    ''' A marker for sites that want to use OAuth '''

class ITokenRequest(component.Interface):
    ''' A token request.  We should be able to adapt this to an IPrincipal,
        using a named adapter.
    '''

class IOAuthPrincipal(IPrincipal):
    domain = schema.TextLine(title=u'Domain: ', default=u'oauth')  # OAuth
    login = schema.TextLine(title=u'Name: ')
    secret = schema.Password(title=u'Password: ')

class IOAuthPrincipalSource(IPrincipalSource):
    '''  Provides a searchable list of principals
    '''
    domain = schema.TextLine(title=u'Default Service: ')
    def new(self, id):
        ''' Returns a new (unidentified) principal '''

    def find(self, **kw):
        ''' Returns a list of principals based upon search criteria '''

