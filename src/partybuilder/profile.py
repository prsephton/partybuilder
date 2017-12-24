''' Manage the currently connected users profile.  This interacts with GW2 api to retrieve the
    users current build.  The user profile may then be shared with the party in order to match 
    traits, weapons/skills, gear bonuses etc.
'''

import grok
import simplejson as json
from interfaces import ILayout, IUser, IUserProfile, Content
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import urlencode
from six.moves.urllib.error import HTTPError
from zope import location
from resource import js_utils

class GW2API(object):
    base = 'https://api.guildwars2.com/v2/'

    def apiRequest(self, ep, key=None, data=None, method='GET'):
        if data is not None or method=='POST':
            req = Request("{}{}".format(self.base, ep))
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            if key is not None:
                req.add_header('Authorization', "Bearer: {}".format(key))
            data = urlencode(data)
            req.add_data(data)
        elif key is None:
            req = Request("{}{}".format(self.base, ep)) # GET without token
        else:
            if data is None: data = {}
            data['access_token'] = key
            data = urlencode(data)
            req = Request("{}{}?{}".format(self.base, ep, data))     
        try:
            res = urlopen(req).read()
            return json.loads(res)
        except HTTPError as e:
            raise
    
    def account(self, key):
        return self.apiRequest('account', key)
    
    def characters(self, key):
        return self.apiRequest('characters', key)
    
    def character_core(self, key, character):
        ep = 'characters/{}'.format(character)
        return self.apiRequest(ep, key)
    
    def character_equipment(self, key, character):
        ep = 'characters/{}/equipment'.format(character)
        ret = self.apiRequest(ep, key)
        for item in ret['equipment']:
            item['id'] = self.items(item['id'])
            if 'upgrades' in item:
                item['upgrades'] = [self.items(i) for i in item['upgrades']]
            if 'infusions' in item:
                item['infusions'] = [self.items(i) for i in item['infusions']]
            if 'skin' in item:
                item['skin'] = self.skins(item['skin'])
        return ret
                
    def character_skills(self, key, character):
        ep = 'characters/{}/skills'.format(character)
        return self.apiRequest(ep, key)

    def character_specializations(self, key, character):
        ep = 'characters/{}/specializations'.format(character)
        return self.apiRequest(ep, key)
    
    def skins(self, a_id):
        return self.apiRequest('skins/{}'.format(a_id))
    
    def items(self, a_id):
        return self.apiRequest('items/{}'.format(a_id))

    def itemstats(self, a_id):
        return self.apiRequest('itemstats/{}'.format(a_id))
    
    def skills(self, a_id):
        return self.apiRequest('skills/{}'.format(a_id))
    
    def specializations(self, a_id):
        return self.apiRequest('specializations/{}'.format(a_id))
    
    def traits(self, a_id):
        return self.apiRequest('traits/{}'.format(a_id))
    
    
    
class UserProfile(grok.Model):
    grok.implements(IUserProfile, ILayout)
    
    characters = []
    selected = ''
    
    def __init__(self, user):
        self.user = user
    
    def update(self):
        self.account = GW2API().account(self.user.gw2_apikey)
        self.characters = GW2API().characters(self.user.gw2_apikey)
        if len(self.selected)==0: self.selected = self.characters[0]
        self.core = GW2API().character_core(self.user.gw2_apikey, self.selected)
        self.skills = GW2API().character_skills(self.user.gw2_apikey, self.selected)
        self.equipment = GW2API().character_equipment(self.user.gw2_apikey, self.selected)
        self.specializations = GW2API().character_specializations(self.user.gw2_apikey, self.selected)

    def gear(self):
        items = ["Helm", "Shoulders", "Gloves", "Coat", "Leggings", "Boots"]
        refs = {}
        equipment = self.equipment['equipment']
        for e in equipment:
            if 'slot' in e and e['slot'] in items:
                refs[e['slot']] = e
        return [refs[i] for i in items]
    
    
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
        else:
            if 'character' in self.request:
                self.context.selected = self.request['character']
            self.context.update()
            
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
        
