'''
    Some standard token adapters.  This fills in some user detail from the
    oauth2 provider.

    This is where a new user is added to our PrincipalSources if the user
    does not already exist.
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


class FacebookTokenToUser(grok.Adapter):
    ''' A token user for Facebook
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Facebook')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Facebook.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'Facebook'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class TwitterTokenToUser(grok.Adapter):
    ''' A token user for Twitter
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Twitter')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Twitter.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'Twitter'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class LinkedInTokenToUser(grok.Adapter):
    ''' A token user for LinkedIn
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'LinkedIn')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Twitter.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'LinkedIn'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class RedditTokenToUser(grok.Adapter):
    ''' A token user for Reddit
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Reddit')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Reddit.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'Reddit'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class GithubTokenToUser(grok.Adapter):
    ''' A token user for Github
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'GitHub')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "GitHub.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'GitHub'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class InstagramTokenToUser(grok.Adapter):
    ''' A token user for LinkedIn
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Instagram')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Instagram.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'Instagram'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


class MixerTokenToUser(grok.Adapter):
    ''' A token user for Mixer
    '''
    grok.context(ITokenRequest)
    grok.implements(IOAuthPrincipal)
    grok.name(u'Mixer')

    def __new__(self, token):
        app = grok.getApplication()
        users = IOAuthPrincipalSource(app)
        uid = "Mixer.{}".format(token.info['id_token'])

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = found[0]

        user.authInfo = token.info
        user.domain = u'Mixer'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


