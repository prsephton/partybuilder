from bs4 import BeautifulSoup
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import urlencode
from six.moves.urllib.error import HTTPError, URLError
from interfaces import IFact
from zope import component

BASE = "https://wiki.guildwars2.com"
SKILLS = {}

def get_url(url):
    try:
        return urlopen(url).read()
    except HTTPError as e:
        raise
    except URLError as e:
        pass

class Skill(object):
    title = None
    _image = None
    
    def __init__(self, title, stype):
        self.title = title
        self.stype = stype
        
    @property
    def href(self): return self._href
    
    @href.setter    
    def href(self, href): self._href = href
    
    @property
    def image(self): return self._image
    
    @image.setter
    def image(self, image): self._image = image

def get_stacks(hdr):
    h = hdr.split(" ")
    if len(h)==2:
        stacks, q = h  
    else:
        stacks, q = None, h[0]
    if stacks and stacks.isdigit():
        return int(stacks), q
    return None, hdr

def process_stats(items):
    for i in items:
        pass


def process_skill_detail(skill):
    factMaker = component.getUtility(IFact)
    url = BASE + skill.href
    html = get_url(url)
    soup = BeautifulSoup(html, "html.parser")
    parser_output = soup.find("div", attrs={"class":"mw-parser-output"})
    dsc = parser_output.select("blockquote div p")
    if len(dsc): skill.description = dsc[0].text
    
    facts = parser_output.select("blockquote div dl dd")
    factset = []
    for fact in facts:
        text = fact.text.strip()
        sline = text.split(":")
        if len(sline)==2:
            hdr, fact = sline
        else:
            hdr, fact = sline[0], ''
        hdrinfo  = [h.split(")")[0].strip() for h in hdr.split("(")]
        factinfo = [f.split(")")[0].strip() for f in fact.split("(")]

        
        stacks, item = get_stacks(hdrinfo[0])
        if   item == "Healing":       ftype = item; fdata = {'hit_count': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Distance":      ftype = item; fdata = {'distance': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Range":         ftype = item; fdata = {'value': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Radius":        ftype = item; fdata = {'distance': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Duration":      ftype = item; fdata = {'duration': factinfo[0], 'text': text, 'type':ftype}        
        elif item == "Adjust":        ftype = item; fdata = {'value':factinfo[0], 'target':hdr, 'text': text, 'type':ftype}
        elif item == "ComboField":    ftype = item; fdata = {'field_type': factinfo[0], 'text': text, 'type':ftype}
        elif item == "ComboFinisher": ftype = item; fdata = {'finisher_type': factinfo[0], 'percent':'', 'text': text, 'type':ftype}
        elif item == "HealingAdjust": ftype = item; fdata = {'hit_count': factinfo[0], 'text': text, 'type':ftype}
        elif item == "NoData":        ftype = item; fdata = {'text': text, 'type':ftype}
        elif item == "Number":        ftype = item; fdata = {'value': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Percent":       ftype = item; fdata = {'percent': factinfo[0], 'text': text, 'type':ftype}
        elif item == "PrefixedBuff":  ftype = item; fdata = {'duration': factinfo[0], 'status':item, 'description':text, 
                                                             'apply_count':stacks, 'text': text, 'type':ftype}
        elif item == "Recharge":      ftype = item; fdata = {'value': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Time":          ftype = item; fdata = {'duration': factinfo[0], 'text': text, 'type':ftype}
        elif item == "Unblockable":   ftype = item; fdata = {'text': text, 'type':ftype}        
        elif item == "Damage":        ftype = item; fdata = {'hit_count': factinfo[0], 'dmg_multiplier':factinfo[1], 'text': text, 'type':ftype}
        elif item in ["Aegis","Alacrity","Fury","Might","Protection","Quickness","Regeneration","Resistance",
                      "Retaliation","Stability","Swiftness","Vigor"]:
            if stacks:
                ftype = 'Buff'; fdata = {'description': factinfo[0], 'status':item,  'duration':hdrinfo[1], 
                                         'apply_count':stacks, 'text': text, 'type':ftype}
            elif len(factinfo) > 1:
                ftype = 'Buff'; fdata = {'status':item, 'duration':factinfo[1], 'text': text, 'type':ftype}                             
            elif len(hdrinfo) > 1:
                ftype = 'Buff'; fdata = {'status':item, 'duration':hdrinfo[1], 'text': text, 'type':ftype}                             
            else:
                ftype = 'Buff'; fdata = {'status':item, 'text': text, 'type':ftype}                             
        elif item in ["Immobilize", "Vulnerability", "Poisoned", "Bleeding", "Burning", "Confusion", "Confusion", 
                      "Blinded", "Chilled", "Fear", "Slow", "Taunt", "Weakness"]:
            if stacks:
                ftype = 'Buff'; fdata = {'description': factinfo[0], 'status':item,  'duration':hdrinfo[1], 
                                         'apply_count':stacks, 'text': text, 'type':ftype}
            elif len(factinfo)>1:
                ftype = 'Buff'; fdata = {'status':item, 'duration':factinfo[1],'text': text, 'type':ftype}                
            elif len(hdrinfo) > 1:
                ftype = 'Buff'; fdata = {'status':item, 'duration':hdrinfo[1], 'text': text, 'type':ftype}                             
            else:
                ftype = 'Buff'; fdata = {'status':item, 'text': text, 'type':ftype}                
        elif item in ["Daze", "Float", "Knockback", "Knockdown", "Launch", "Pull", "Sink", "Stun"]:
            if len(factinfo)>1:
                ftype = 'Buff'; fdata = {'status':item, 'duration':factinfo[1],'text': text, 'type':ftype}                
            else:
                ftype = 'Buff'; fdata = {'status':item, 'text': text, 'type':ftype}                
        else: 
            ftype = "Number"; fdata = {'value': factinfo[0], 'text': text, 'type':ftype}
        factset.append(fdata)
    skill.facts = factMaker(factset)
    stats = parser_output.select("div.infobox div.statistics p")
    if len(stats): stats = process_stats(stats[0].children)
    pass

def process_skill_type(stype, link):
    url = BASE + link
    html = get_url(url)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", attrs={"class":"skills"})
    alist = table.select('tr > td:nth-child(1) > span a')
    for a in alist:
        title = a.attrs['title']
        if title in SKILLS:
            skill = SKILLS[title]
        else:
            SKILLS[title] = skill = Skill(title, stype)
        skill.href = a.attrs['href']
        img = a.find("img")
        if img: skill.image = img.attrs["src"]
        process_skill_detail(skill)
        
    pass

def process_skilltypes(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", attrs={"class":"mech2"})
    tr = table.select('tr')
    a = [row.select("th a") for row in tr[1:]]
    for tag in a:
        if len(tag):
            tag = tag[0]
            process_skill_type(tag.text, tag.attrs['href'])

def gw2wikiSkills():
    url = BASE+"/wiki/Skill"
    html = get_url(url)
    process_skilltypes(html)
