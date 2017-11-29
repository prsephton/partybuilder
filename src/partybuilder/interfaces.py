from zope import schema, component

class IUser(component.Interface):
    login = schema.TextLine(title=u'Name: ')
    password = schema.TextLine(title=u'Password: ')
    gw2_appkey = schema.TextLine(title=u'GW2 App Key: ')
    disco_id = schema.TextLine(title=u'Discord ID: ')

class IMember(component.Interface):
    userid = schema.Int(title=u'ID: ')

class IParty(component.Interface):
    party_name = schema.TextLine(title=u'Party Name: ')
    type = schema.Choice(title=u'Type: ', values=[u'WvW', u'PvE', u'PvP'], default=u'WvW')
    view = schema.Choice(title=u'View: ', values=[u'Summary', u'Stats', u'Gear',
                                                  u'Skills', u'CCs', u'Conditions',
                                                  u'Boons', u'Traits'])
#     members = schema.List(title=u'Members', value_type=schema.Int, unique=True, default=[])
