import grok
import simplejson as json

from partybuilder import resource
from interfaces import IUser, IParty, ILayout
from zope import component
from oauth.interfaces import IOAuthSite, IOAuthPrincipalSource
from zope.catalog.interfaces import ICatalog
from zope.schema.fieldproperty import FieldProperty


class User(grok.Model):
    grok.implements(IUser)
    id = FieldProperty(IUser['id'])
    title = FieldProperty(IUser['title'])
    description = FieldProperty(IUser['description'])
    userno = FieldProperty(IUser['userno'])
    domain = FieldProperty(IUser['domain'])
    login = FieldProperty(IUser['login'])
    secret = FieldProperty(IUser['secret'])
    gw2_apikey = FieldProperty(IUser['gw2_apikey'])
    disco_id = FieldProperty(IUser['disco_id'])

    def __init__(self, userno, id=None):
        self.userno = int(userno)
        self.id = id


class Party(grok.Model):
    grok.implements(IParty)

    def __init__(self, partyno):
        self.partyno = partyno


class Users(grok.Container):
    grok.implements(IUser, ILayout, IOAuthPrincipalSource)
    sequence = 0
    domain = u'PartyBuilder'

    def __init__(self):
        super(Users, self).__init__()
        self.sequence = 0

    def __contains__(self, id):
        return len(self.find(id=id))>0

    def new(self, id):
        seq = str(self.sequence)
        self.sequence += 1
        user = self[seq] = User(seq, id=id)
        return self[seq]

    def find(self, **kw):
        catalog = component.getUtility(ICatalog, name='userindex')
        return catalog.searchResults(**kw)


class PrincipalSourceAdapter(grok.Adapter):
    grok.context(IOAuthSite)
    grok.implements(IOAuthPrincipalSource)

    def __new__(self, context):
        return context['users']


class Parties(grok.Container):
    grok.implements(IParty, ILayout)
    sequence = 0
    def __init__(self):
        super(Parties, self).__init__()
        self.sequence = 0


class Partybuilder(grok.Application, grok.Container):
    grok.implements(ILayout, IOAuthSite)

    def __init__(self):
        super(Partybuilder, self).__init__()
        self['users'] = Users()
        self['parties'] = Parties()


class UserIndex(grok.Indexes):
    grok.site(Partybuilder)
    grok.context(User)
    grok.name('userindex')

    id = grok.index.Text()  # an internal Principal ID


class Index(grok.View):
    grok.context(ILayout)
    grok.require('zope.Public')

    def update(self):
        resource.bootstrap.need()
        resource.style.need()



