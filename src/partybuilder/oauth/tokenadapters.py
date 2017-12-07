'''
    Some standard token adapters.  This fills in some user detail from the
    oauth2 provider.
'''
import grok
from interfaces import ITokenRequest, IOAuthPrincipal, IOAuthPrincipalSource
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode

class GoogleTokenToUser(grok.Adapter):
    ''' A google-specific adapter which returns a principal. The token
        passed in is an instance of oauth.TokenRequest.  This should
        have the info needed to identify the principal.
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Google')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Google.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info

        url = u"https://www.googleapis.com/userinfo/v2/me"
        req = Request(url)
        req.add_header("Authorization", "{} {}".format(token.info['token_type'],
                                                       token.info['access_token']))
        res = urlopen(req).read()
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
