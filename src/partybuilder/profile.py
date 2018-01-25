''' Manage the currently connected users profile.  This interacts with GW2 api to retrieve the
    users current build.  The user profile may then be shared with the party in order to match 
    traits, weapons/skills, gear bonuses etc.
'''

import grok
import simplejson as json
import regex as re
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from interfaces import (ILayout, IUser, IUserProfile, Content, IItemCache, 
                        IItemStatsCache, ISkinCache, ITraitsCache, ISkillsCache)
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import urlencode
from six.moves.urllib.error import HTTPError, URLError
from zope import location
from resource import js_utils
from zope import component
from gw2api.v2 import wvw_abilities
from PIL import Image
from StringIO import StringIO
import regex as re


g_overrides = {
        'skills': {
            'Comet': {
                    'attunement': 'Water',
                },
            'Freezing Gust': {
                    'attunement': 'Water',
                },
            'Obsidian Flesh': {
                    'attunement': 'Earth',
                },
            'Magnetic Wave': {
                    'attunement': 'Earth',
                },
            'Gale': {
                    'attunement': 'Air',
                    'slot': 'Weapon_4',
                },
            'Swirling Winds': {
                    'attunement': 'Air',
                },
            'Flamewall': {
                    'attunement': 'Fire',
                },
            'Fire Shield': {
                'slot': 'Weapon_5',
                },
            }
    }


def check_overrides(what, name, attribute):
    global g_overrides
    if what in g_overrides:
        if name in g_overrides[what]:
            if attribute in g_overrides[what][name]:
                return g_overrides[what][name][attribute]
    

class SkillFact(object):
    type = ''
    text = ''
    icon = ''
    description = ''
    duration = ''
    status = None
    apply_count = None
    value = None    
    distance = None
    requires_trait = None
    overrides = None


class Skill(object):
    facts = []
    traited_facts = None
    name = ''
    icon = None
    description = ''
    type = None
    slot = ''
    flags = []
    specialization = None
    skill_choice = None
    categories = None
    weapon_type = None
    id = 0
    flip_skill = None
    chat_link = ''
    
    def __init__(self, api, skill):
        self.id = skill
        skill = api.skills(skill)
        self.name = skill['name']
        global g_overrides
        if 'skills' in g_overrides and self.name in g_overrides['skills']:
            for k, attr in g_overrides['skills'][self.name].items():
                skill[k] = attr
        self.icon = skill['icon']
        self.type = skill['type']
        self.slot = skill['slot']
        self.flags = skill['flags']
        if 'description' in skill: self.description = skill['description']
        if 'specialization' in skill: self.specialization = skill['specialization']
        if 'weapon_type' in skill: self.weapon_type = skill['weapon_type']
        if 'categories' in skill: self.categories = skill['categories']
        if 'attunement' in skill: self.attunement = skill['attunement']

        match = re.match(r"^(.*) Attunement", self.name)
        if match: 
            self.skill_choice = match[1]
        if 'flip_skill' in skill:
            try:
                skill_id = int(skill['flip_skill'])
                self.flip_skill = Skill(api, skill_id)
            finally:
                pass
    
    def getClass(self, skill_choices):
        if skill_choices is None: return 'Other'
        return getattr(self, skill_choices, 'Other')
    
#  Traits for the character are selected in-game.
#  Skills categories are profession skills, weapon skills, heal, utility and elite skill
#  Each skill or fact may have a specialization, and is unavailable unless the skill specialization 
#  is present in the characters set of specializations.
#  Each skill has a list of facts, which may be overridden by the list of traited facts.
#  Traited facts have a 'required trait' which must be selected by the character for the override
#  to be in effect.
#  If a skill has a flip_skill, this would be the next skill in sequence, but its availability
#  depends on a character having the correct specialization.
#  Traits can have skills which trigger given specific condition (eg. <50% health or when using 
#  a heal skill).  Such skills in turn have lists of skill facts.

class GW2API(object):
    base = 'https://api.guildwars2.com/v2/'
    app = None
    
    def __init__(self):
        self.app = grok.getApplication()
    
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
        for retries in range(3):
            try:
                res = urlopen(req).read()
                return json.loads(res)
            except HTTPError as e:
                raise
            except URLError as e:
                pass
    
    def account(self, key):
        return self.apiRequest('account', key)
    
    def characters(self, key):
        return self.apiRequest('characters', key)
    
    def character_core(self, key, character):
        ep = 'characters/{}'.format(character)
        ret = self.apiRequest(ep, key)
        if ret is None: return None
        for item in ret['equipment']:
            item['id'] = self.items(item['id'])
            if 'upgrades' in item:
                item['upgrades'] = [self.items(i) for i in item['upgrades']]
            if 'infusions' in item:
                item['infusions'] = [self.items(i) for i in item['infusions']]
            if 'skin' in item:
                item['skin'] = self.skins(item['skin'])
            if 'stats' in item:
                item['stats']['id'] = self.itemstats(item['stats']['id'])
        for gmode in ret['specializations']:
            for spec in ret['specializations'][gmode]:
                if spec and 'id' in spec: 
                    spec['id'] = self.specializations(spec['id'])
                    spec['traits'] = [self.traits(trait) for trait in spec['traits']]
        for gmode in ret['skills']:
            s = ret['skills'][gmode]
            s['heal'] = Skill(self, s['heal'])
            s['elite'] = Skill(self, s['elite'])
            s['utilities'] = [Skill(self, u) for u in s['utilities']]
            ret['skills'][gmode] = s
            
        return ret
    
    def get_profession(self, profession):
        ep = 'professions/{}'.format(profession)
        return self.apiRequest(ep)
        
    def skins(self, a_id):
        cache = ISkinCache(self.app)
        val = cache[a_id]
        if val is None:
            val = self.apiRequest('skins/{}'.format(a_id))
            cache[a_id] = val
        return val
    
    def items(self, a_id):
        cache = IItemCache(self.app)
        val = cache[a_id]
        if val is None:
            val = self.apiRequest('items/{}'.format(a_id))
            cache[a_id] = val
        return val

    def itemstats(self, a_id):
        cache = IItemStatsCache(self.app)
        val = cache[a_id]
        if val is None:
            val = self.apiRequest('itemstats/{}'.format(a_id))
            cache[a_id] = val
        return val
    
    def skills(self, a_id):
        cache = ISkillsCache(self.app)
        val = cache[a_id]
        if val is None:
            val = self.apiRequest('skills/{}'.format(a_id))
            cache[a_id] = val
        return val
    
    def specializations(self, a_id):
        spec = self.apiRequest('specializations/{}'.format(a_id))
        for key in ['minor_traits', 'major_traits']:
            spec[key] = [self.traits(trait) for trait in spec[key]]
        return spec
    
    def traits(self, a_id):
        cache = ITraitsCache(self.app)
        val = cache[a_id]
        if val is None:
            val = self.apiRequest('traits/{}'.format(a_id))
            cache[a_id] = val
        return val
        

class SpecImage(grok.Model):
    fn = 'noname'
    image = ''
    url = ''
    
    def __init__(self, url):
        self.fn = url[url.rfind("/")+1:]
        self.url = url
        
    def retrieve(self):
        try:
            fd = StringIO(urlopen(self.url).read())
            im = Image.open(fd)
            _w, h = im.size
            box = (0, h-200, 650, 200)
            region = im.crop(box)
            box = (500, 100)
            region = region.resize(box)
            bytes = StringIO()
            region.save(bytes, format='PNG')
            self.image = bytes.getvalue()
        except Exception, e:
            print "Cannot retrieve image at url: %s" % self.url
            print "Error %s" % str(e)

class SpecImageView(grok.View):
    grok.context(SpecImage)
    grok.require('zope.Public')
    grok.name('index')
    
    def render(self):
        self.response.setHeader('Content-Type', "image/png")
        disposition = "inline; filename='{}'".format(self.context.fn)
        self.response.setHeader("Content-Disposition", disposition)
        return self.context.image


class UserProfile(grok.Model):
    grok.implements(IUserProfile, ILayout)

    # Derived stats    
    health = 0            # 1 Vitality = 10 health)
    armor = 0             # Toughness + Defense
    crit_chance = 0       # (Crit Chance = 5% + Precision / 21
    crit_dmg = 0          # (Crit Dmg = 150% + by Ferocity/15
    boon_duration = 0     # Increased by Concentration (15 = 1%)
    cond_duration = 0     # Increased by Expertise (15 = 1%)
    
    base_health = {'Warrior':9212, 'Necromancer':9212,
                   'Revenant':5922, 'Engineer':5922, 'Ranger':5922, 'Mesmer':5922,
                   'Guardian':1645, 'Thief':1645, 'Elementalist':1645 }
    
    stats = PersistentDict()
    runes = PersistentDict()
    buffs = PersistentList()
    
    selected_weapon = 0
    selected_traits = []
    characters = []
    selected = ''
    refresh = False
    skill_choices = None
    skill_choice = None
    gear = []
    trinkets = []
    amulet = []
    backpack = []
    aquatic = []
    game_modes = ["pve", "pvp", "wvw"]
    gmode = "wvw"
    spec_bg = grok.Container()
    grok.traversable('spec_bg')
    
    def __init__(self, user):
        location.locate(self.spec_bg, self, 'spec_bg')
        self.user = user
        
    def update(self):
        location.locate(self.spec_bg, self, 'spec_bg')
        account = GW2API().account(self.user.gw2_apikey)
        if account is not None:
            self.account = account
        characters = GW2API().characters(self.user.gw2_apikey)
        if characters is not None:
            self.characters = characters
#        self.refresh=True
        if len(self.selected)==0: 
            self.selected = self.characters[0]
            self.refresh = True
        if self.refresh:
            core = GW2API().character_core(self.user.gw2_apikey, self.selected)
            if core is not None: 
                self.core = core
#            self.equipment = GW2API().character_equipment(self.user.gw2_apikey, self.selected)
#            self.skills = GW2API().character_skills(self.user.gw2_apikey, self.selected)
#            self.specializations = GW2API().character_specializations(self.user.gw2_apikey, self.selected)
            self.refresh = False
            
        self.stats = PersistentDict({'Power': 1000, 'Precision': 1000, 'Toughness': 1000, 'Vitality':1000,
                                     'Defense':0, 'ConditionDamage': 0, 'CritDamage':0,
                                     'Concentration':0, 'Expertise':0, 'Ferocity':0, 'Healing':0,
                                     'BoonDuration':0, 'ConditionDuration':0
                                     })
        self.runes = PersistentDict()
        self.buffs = PersistentList()
        
        self.gear = self._gear()
        self.trinkets = self._trinkets()
        self.amulet = self._amulet()
        self.backpack = self._backpack()
        self.weapons = self._weapons()
        self.aquatic = self._aquatic()
        self.profession = GW2API().get_profession(self.core['profession'])
        self.skill_choices = None
        if self.profession['name'] == 'Elementalist':
            self.skill_choices = 'attunement'
            if self.skill_choice is None: self.skill_choice = 'Fire'
        self.prof_skills = self._profession_skills()
        self.weap_skills = self._weapon_skills()

        self.rune_bonuses = []
        for r in self.runes.values():
            b = r['rune']['bonuses'][:r['count']]
            for effect in b:
                self.rune_bonuses.append(effect)
                if effect.find(' to All Stats')>0:
                    perc = int(effect.split(' ')[0])
                    for stat in ['Power', 'Precision', 'Toughness', 'Vitality', 'Ferocity', 'Healing', 'ConditionDamage']:
                        self.stats[stat] += perc
                elif effect.find('% Boon Duration') > 0:
                    perc = int(effect.split('%')[0])
                    self.stats['BoonDuration'] += perc * 15
                elif self._stat_effect(effect):
                    pass
                else:
                    self.buffs.append(effect)

        self.health = self.stats['Vitality'] * 10 + self.base_health[self.core['profession']]
        self.armor = self.stats['Toughness'] + self.stats['Defense']
        self.crit_chance = (self.stats['Precision']-916) / 21.0
        self.crit_dmg = 150 + (self.stats['CritDamage'] + self.stats['Ferocity']) / 15.0
        self.boon_duration = (self.stats['BoonDuration'] + self.stats['Concentration']) / 15.0
        self.cond_duration = (self.stats['ConditionDuration'] + self.stats['Expertise']) / 15.0
        
#         for i in list(self.spec_bg.keys()):
#             del self.spec_bg[i]

        self.selected_traits = []
        for spec in self.specs():
            for t in spec['traits']:
                if 'description' in t:
                    self.buffs.append("%s - %s"%(t['name'], t['description']))
                else:
                    self.buffs.append(t['name'])            
            img = SpecImage(spec['id']['background'])
            if img.fn not in self.spec_bg.keys():
                img.retrieve()
                self.spec_bg[img.fn] = img
            spec['id']['img_no'] = img.fn
            self.selected_traits.extend([t['name'] for t in spec['traits']])
            
        
        pass

    def gear_title(self, gear):
        try:
            if 'stats' in gear:
                stats = [ "%s: +%s" % (n, s) for n, s in gear['stats']['attributes'].items()]
                return "\n".join(stats)
            else:
                attributes = gear['id']['details']['infix_upgrade']['attributes']
                return "\n".join(['%s: +%s' % (a['attribute'], a['modifier']) for a in attributes])
        except Exception, e:
            print "Cannot determine gear title for %s" % gear
            print "%s" % str(e)
        return ''

    def upgrade_title(self, upgrade, idx):
        try:
            if 'details' in upgrade and 'type' in upgrade['details']:
                if upgrade['details']['type'] == 'Rune':
                    return self.rune_bonuses[idx]
        except Exception, e:
            print "Cannot determine upgrade title for %s" % upgrade
            print "%s" % str(e)
        return ''
    
    def statlist(self):
        for s in ["Power", "Precision", "Toughness", "Vitality", "Healing", "ConditionDamage"]:
            yield {'name':s, 'value': self.stats[s], 'unit': ''}
        yield {'name':'Health', 'value': self.health, 'unit': ''}
        yield {'name':'Armour', 'value': self.armor, 'unit': ''}
        yield {'name':'Crit Chance', 'value': round(self.crit_chance, 2), 'unit': '%'}
        yield {'name':'Crit Damage', 'value': round(self.crit_dmg, 2), 'unit': '%'}
        yield {'name':'Boon Duration', 'value': round(self.boon_duration, 2), 'unit': '%'}
        yield {'name':'Cond Duration', 'value': round(self.cond_duration, 2), 'unit': '%'}
        
        
    def specs(self):
        return self.core['specializations'][self.gmode]        
        
    def _stat_effect(self, effect):
        exp = re.search(r'\+(.*) (Power|Precision|Toughness|Vitality|Defense|Healing|Concentration|Expertise)', effect)
        if (exp and len(exp)==3):
            self.stats[exp[2]] += int(exp[1])
            return True
        
    def _process_attributes(self, attributes):
        for a, i in attributes.items():
            if a in self.stats:
                self.stats[a] += i
            else:
                self.stats[a] = i
                
    def _process_details(self, details):
        if 'defense' in details:
            self.stats['Defense'] += details['defense']
        if 'infix_upgrade' in details:
            for a in details['infix_upgrade']['attributes']:
                if a['attribute'] in self.stats:
                    self.stats[a['attribute']] += a['modifier']
                else:
                    self.stats[a['attribute']] = a['modifier']
            if 'buff' in details['infix_upgrade']:
                pass
        else:
            pass
#                 self.buffs.append(details['infix_upgrade']['buff'])
            
    def _check_stats(self, e):
        if 'id' in e and type(e['id']) is dict:
            if 'details' in e['id']:
                self._process_details(e['id']['details'])
        
        if 'stats' in e and 'attributes' in e['stats']:
            for a, i in e['stats']['attributes'].items():
                if a in self.stats:
                    self.stats[a] += i
                else:
                    self.stats[a] = i
            
        if 'infusions' in e:
            for i in e['infusions']:
                if i['type'] == 'UpgradeComponent' and 'details' in i:
                    self._process_details(i['details'])
                else:
                    print "Not processing infusion type: %s" % i['type']
                
        if 'upgrades' in e:
            for u in e['upgrades']:
                if u['type'] == 'UpgradeComponent' and 'details' in u:
                    r = u['details']
                    if r['type'] == 'Rune':
                        if u['name'] in self.runes:
                            self.runes[u['name']]['count'] += 1
                        else:
                            self.runes[u['name']] = {'rune': r, 'count':1}
                    else:
                        self._process_details(r)                    
                else:
                    print 'Not processing upgrade type=%s' % u['type']

    
    def weaponset(self, w):
        wset = self.weapons[w]
        items = [item['id']['details']['type'] for item in wset]
        return "/".join(items)
    
    def select_weapon(self, current):
        self.selected_weapon = current
    
    def weapon_skills(self):
        if self.selected_weapon >= len(self.weapons): self.selected_weapon = 0
        skills = self.weap_skills[self.selected_weapon]
        if self.skill_choice and self.skill_choice in skills:
            skills = skills[self.skill_choice].values()
        elif 'Other' in skills:
            skills = skills['Other'].values()
        else:
            skills = []
        return [s for s in skills if self._spec_check(s)]

    def utility_skills(self):
        s = self.core['skills'][self.gmode]
        skills = [s['heal']]
        skills.extend(s['utilities'])
        skills.append(s['elite'])
        return skills
        
    def describe_skill(self, s):
        return ''

    def _spec_check(self, item):
        specs = set([x['traits'][0]['specialization'] for x in self.specs()])
        if type(item) is dict:
            if 'specialization' in item:
                return item['specialization'] in specs
        else:
            if hasattr(item, 'specialization'):
                if item.specialization is not None:
                    return item.specialization in specs
        return True

    def _profession_skills(self):
        api = GW2API()
        p = self.profession
        prof_skills = [skill for skill in p['skills'] if skill['type']=='Profession']
        from collections import OrderedDict
        skills = OrderedDict()
        for s in prof_skills:
            skill = s['id'] = Skill(api, s['id'])
            if self._spec_check(skill):
                if skill.categories is not None:
                    for cat in skill.categories:
                        if cat not in skills: skills[cat] = {}
                        skills[cat][skill.slot] = skill
                elif self.skill_choices == 'attunement':
                    cat = "attunement"
                    if cat not in skills: skills[cat] = {}
                    skills[cat][skill.slot] = skill
                else:
                    cat = 'Other'
                    if cat not in skills: skills[cat] = {}
                    skills[cat][skill.slot] = skill
        for cat in skills:
            od = OrderedDict()
            for k in sorted(skills[cat].keys()):
                od[k] = skills[cat][k] 
            skills[cat] = od
        return skills.values()

    def _weapon_skills(self):
        api = GW2API()
        pref = self.profession['weapons']
        from collections import OrderedDict
        skills = []
        for slot in self.weapons:  # fill in weapon skills info
            skillset = {}
            for w in slot:
                wtype = w['id']['details']['type']
                w_skills = [s['id'] for s in pref[wtype]['skills']]
                w_skills = [Skill(api, id) for id in w_skills]
                for s in w_skills:
                    c = s.getClass(self.skill_choices)
                    if c not in skillset: skillset[c] = {}
                    skillset[c][s.slot] = s
            for c in skillset:
                od = OrderedDict()
                for s in sorted(skillset[c].keys()):
                    od[s] = skillset[c][s]
                skillset[c] = od
            skills.append(skillset)
        
        return skills
    
    def _weapons(self):
        refs = {}
        
        equipment = self.core['equipment']
        
        items = ["WeaponA1", "WeaponA2"]
        for e in equipment:
            if 'slot' in e and e['slot'] in items:
                refs[e['slot']] = e                    
        weapons_a = [refs[i] for i in items if i in refs]
        
        items = ["WeaponB1", "WeaponB2"]
        for e in equipment:
            if 'slot' in e and e['slot'] in items:
                refs[e['slot']] = e                    
        weapons_b = [refs[i] for i in items if i in refs]
        if len(weapons_b):
            weapons = [weapons_a, weapons_b]
        else:
            weapons = [weapons_a]
        
        if self.selected_weapon >= len(weapons):
            self.selected_weapon = 0
            
        current = weapons[self.selected_weapon] 
        
        for c in current:
            self._check_stats(c)            
        return weapons

    
    def _trinkets(self):
        refs = {}
        items = ["Accessory1", "Accessory2", "Ring1", "Ring2"]
        equipment = self.core['equipment']
        for e in equipment:
            if 'slot' in e and e['slot'] in items:                    
                self._check_stats(e)            
                refs[e['slot']] = e
                    
        return [refs[i] for i in items]

        
    def _backpack(self):
        slot = 'Backpack'
        equipment = self.core['equipment']
        for e in equipment:
            if 'slot' in e and e['slot']==slot:
                self._check_stats(e)
                return [e]
            
    def _amulet(self):
        slot = 'Amulet'
        equipment = self.core['equipment']
        for e in equipment:
            if 'slot' in e and e['slot']==slot:
                self._check_stats(e)
                return [e]
            
    def _gear(self):
        items = ["Helm", "Shoulders", "Coat", "Gloves", "Leggings", "Boots"]
        refs = {}
        equipment = self.core['equipment']
        for e in equipment:
            if 'slot' in e and e['slot'] in items:                    
                self._check_stats(e)            
                refs[e['slot']] = e
                    
        return [refs[i] for i in items]
    
    def _aquatic(self):
        refs = {}
        items = ["WeaponAquaticA", "WeaponAquaticB", "HelmAquatic"]
        equipment = self.core['equipment']
        for e in equipment:
            if 'slot' in e and e['slot'] in items:
                refs[e['slot']] = e
    
        return [refs[i] for i in items if i in refs]
        
    
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
        if "refresh_char" in self.request:
            self.context.refresh = True
        if not user.gw2_apikey or len(user.gw2_apikey) == 0:
            self.needs_key = True
        else:
            if 'character' in self.request:
                self.context.selected = self.request['character']
                self.context.refresh = True
            if 'gmode' in self.request:
                self.context.gmode = self.request['gmode']
            if 'attunement' in self.request:
                self.context.skill_choice = self.request['attunement']
            if 'weapon' in self.request:
                self.context.select_weapon(int(self.request['weapon']))
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
        
