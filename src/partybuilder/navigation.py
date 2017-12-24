#_____________________________________________________________________________________________
# Display a menu in the title bar for user navigation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import grok

from interfaces import ILayout, IBuilderApp, IUserProfile

class Navigation(grok.ViewletManager):
    grok.context(ILayout)


class NavigationItem(grok.Viewlet):
    grok.viewletmanager(Navigation)
    grok.require('builder.Authenticated')
    grok.template('navigationitem')
    grok.baseclass()
    title = u'Undefined Title'
    link = '#'    
    

class Profile(NavigationItem):
    grok.context(IBuilderApp)
    title = u'Profile'
    grok.order(10)

    def update(self):
        self.link = self.view.url(self.context, 'profile')


class Parties(NavigationItem):
    grok.context(IBuilderApp)
    title = u'Parties'
    grok.order(20)
    
    def update(self):
        self.link = self.view.url(self.context, 'parties')


class ProfileParties(NavigationItem):
    grok.context(IUserProfile)
    title = u'Parties'
    grok.order(20)
    
    def update(self):
        self.link = self.view.url(grok.getApplication(), 'parties')

