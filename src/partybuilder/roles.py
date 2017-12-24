import grok
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from oauth2.interfaces import IOAuthenticatedEvent

class Authenticated(grok.Permission):
    grok.name('builder.Authenticated')
    grok.title(u'An authenticated user')

@grok.subscribe(IOAuthenticatedEvent)
def authenticated(user):
    ''' Come here when a user has been authenticated via OAuth '''
    user = user.object
    print 'Authenticated user [%s]' % user.title
    pm = IPrincipalPermissionManager(grok.getApplication())
    pm.grantPermissionToPrincipal('builder.Authenticated', user.id)
    

