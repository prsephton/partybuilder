import grok

from partybuilder import resource
from interfaces import IUser, IParty, ILayout


class User(grok.Model):
    grok.implements(IUser)

    def __init__(self, userid):
        self.userid = userid


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
