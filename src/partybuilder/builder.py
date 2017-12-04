import grok

from partybuilder import resource
from interfaces import IUser, IParty, ILayout
from zope.security.interfaces import IPrincipal
from partybuilder.oauth import ITokenRequest
from zope.catalog.interfaces import ICatalog
from zope.schema.fieldproperty import FieldProperty
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode
import simplejson as json


class User(grok.Model):
    grok.implements(IUser, IPrincipal)
    id = FieldProperty(IPrincipal['id'])
    title = FieldProperty(IPrincipal['title'])
    description = FieldProperty(IPrincipal['description'])
    userid = FieldProperty(IUser['userid'])
    domain = FieldProperty(IUser['domain'])
    login = FieldProperty(IUser['login'])
    secret = FieldProperty(IUser['secret'])
    gw2_apikey = FieldProperty(IUser['gw2_apikey'])
    disco_id = FieldProperty(IUser['disco_id'])

    def __init__(self, userid):
        self.userid = userid


class GoogleTokenToUser(grok.Adapter):
    ''' A google-specific adapter which returns a principal. '''
    grok.context(ITokenRequest)
    grok.implements(IPrincipal)
    grok.name(u'Google')

    def __new__(self, token):
        app = grok.getApplication()
        users = app['users']
        uid = "Google.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if not found or len(found)==0:
            user = users.new()
            user.id = uid
        else:
            user = found[0]

        user.authInfo = token.info

        url = u"https://www.googleapis.com/userinfo/v2/me"
        args = urlencode(Authorization="{} {}".format(token.info['token_type'],
                                                      token.info['access_token']))
        res = urlopen("{}&{}".format(url, args)).read()
        if res: res = json.loads(res)
        if res is None:
            user.title = u''
            user.description = u''
        else:
            user.title = res['name']
            res.description = u'{} {}'.format(res['given_name'], res['family_name'])

        user.domain = u'Google'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class Party(grok.Model):
    grok.implements(IParty)

    def __init__(self, party_id):
        self.party_id = party_id


class Users(grok.Container):
    grok.implements(IUser, ILayout)
    sequence = 0
    def __init__(self):
        super(Users, self).__init__()
        self.sequence = 0

    def new(self):
        seq = str(self.sequence)
        self.sequence += 1
        self[seq] = User(seq)
        return self[seq]

    def find(self, **kw):
        catalog = component.getUtility(ICatalog, name='userindex')
        return catalog.searchResults(**kw)


class Parties(grok.Container):
    grok.implements(IParty, ILayout)
    sequence = 0
    def __init__(self):
        super(Parties, self).__init__()
        self.sequence = 0


class Partybuilder(grok.Application, grok.Container):
    grok.implements(ILayout)

    def __init__(self):
        super(Partybuilder, self).__init__()
        self['users'] = Users()
        self['parties'] = Parties()


class Index(grok.View):
    grok.context(ILayout)

    def update(self):
        resource.style.need()


class UserIndex(grok.Indexes):
    grok.site(Partybuilder)
    grok.context(User)
    grok.name('userindex')

    id = grok.index.Text()  # an internal Principal ID


