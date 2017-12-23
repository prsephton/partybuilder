from zope import schema, component
from hiddenwidgets import HiddenInt
from oauth2.interfaces import IOAuthPrincipal

class ILayout(component.Interface):
    ''' Our layout marker interface '''

class IUser(IOAuthPrincipal):
    userno = HiddenInt(title=u'')
    gw2_apikey = schema.TextLine(title=u'GW2 App Key: ')
    disco_id = schema.TextLine(title=u'Discord ID: ')

class IParty(component.Interface):
    partyno = HiddenInt(title=u'')
    owner= schema.Int(title=u'Owner ID: ')
    party_name = schema.TextLine(title=u'Party Name: ')
    type = schema.Choice(title=u'Type: ', values=[u'WvW', u'PvE', u'PvP'], default=u'WvW')
    view = schema.Choice(title=u'View: ', values=[u'Summary', u'Stats', u'Gear',
                                                  u'Skills', u'CCs', u'Conditions',
                                                  u'Boons', u'Traits'])
    members = schema.List(title=u'Members', value_type=schema.Object(schema=IUser),
                          unique=True, default=[])

