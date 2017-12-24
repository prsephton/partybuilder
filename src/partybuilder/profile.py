''' Manage the currently connected users profile.  This interacts with GW2 api to retrieve the
    users current build.  The user profile may then be shared with the party in order to match 
    traits, weapons/skills, gear bonuses etc.
'''

import grok
from interfaces import ILayout, IUser, IUserProfile, Content
from zope import location
from resource import js_utils

class UserProfile(grok.Model):
    grok.implements(IUserProfile, ILayout)
    
    def __init__(self, user):
        self.user = user
        

class CurrentUserProfile(grok.Adapter):
    grok.context(IUser)
    grok.implements(IUserProfile)
    
    def __new__(self, user):
        profile = getattr(user, 'profile', None)
        if profile is None:
            profile = user.profile = UserProfile(user)
            location.locate(profile, user, 'profile')
        return profile


class UserProfileViewlet(grok.Viewlet):
    grok.context(UserProfile)
    grok.viewletmanager(Content)
    grok.require('builder.Authenticated')
    
    needs_key = False
    user = None
    
    def update(self):
        self.user = user = IUser(self.context)
        if "reset_gw2key" in self.request:
            user.gw2_apikey = u""
        if len(user.gw2_apikey) == 0:
            self.needs_key = True
        js_utils.need()
        
        
class ProfileUser(grok.Adapter):
    grok.context(UserProfile)
    grok.implements(IUser)

    def __new__(self, profile):
        return profile.__parent__


class ApiKey(grok.EditForm):
    grok.context(UserProfile)
    form_fields = grok.Fields(IUser).select('gw2_apikey')    
    grok.require('builder.Authenticated')

    def setUpWidgets(self, ignore_request=False):
        super(ApiKey, self).setUpWidgets(ignore_request)
        self.widgets['gw2_apikey'].displayWidth=68
    
    @grok.action(u'Apply')
    def apply(self, **data):
        self.applyData(self.context, **data)
        self.redirect(self.request.URL)
        
