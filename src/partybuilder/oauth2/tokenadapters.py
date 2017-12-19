'''
    Some standard token adapters.  This fills in some user detail from the
    oauth2 provider.

    This is where a new user is added to our PrincipalSources if the user
    does not already exist.
'''
import grok
import simplejson as json
from interfaces import ITokenRequest, IOAuthPrincipal, IOAuthPrincipalSource
from six.moves.urllib.request import urlopen, Request
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

        url = u"https://www.googleapis.com/userinfo/v2/me"
        req = Request(url)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "{} {}".format(token.info['token_type'],
                                                       token.info['access_token']))
        res = urlopen(req).read()
        if res: res = json.loads(res)
        if res is None:
            return None
        else:
            uid = u"Google.{}".format(res['id'])
            found = users.find(id=uid)
            if len(found)==0:
                user = users.new(id=uid)
            else:
                user = list(found)[0]

            user.authInfo = token.info
            user.title = unicode(res['name'])
            user.description = u'{} {}'.format(res['given_name'], res['family_name'])
            user.domain = u'Google'
            user.login = unicode(token.info['id_token'])
            user.secret = unicode(token.info['access_token'])
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
        uri = "https://api.twitter.com/1.1/account/verify_credentials.json"

        req = Request(url)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "{} {}".format(token.info['token_type'],
                                                       token.info['access_token']))
        res = urlopen(req).read()
        if res: res = json.loads(res)
        if res is None:
            return None
        else:
            print "result=%s" % res
            uid = u"Twitter.{}".format(res['id'])

            found = users.find(id=uid)
            if len(found)==0:
                user = users.new(id=uid)
            else:
                user = list(found)[0]

            user.authInfo = token.info
            user.domain = u'Twitter'
            user.login = uid
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

        url = u"https://graph.facebook.com/me"
        print "User token info found: %s" % token.info
        req = Request(url)
        
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "{} {}".format(token.info['token_type'],
                                                       token.info['access_token']))
        req.add_data(dict(access_token=token.info['access_token']))
        res = urlopen(req).read()
        if res: res = json.loads(res)
        if res is None:
            return None
        else:
            print "Personal info returned: %s" % res
            uid = u"Facebook.{}".format(res['id'])
            found = users.find(id=uid)
            if len(found)==0:
                user = users.new(id=uid)
            else:
                user = list(found)[0]

            user.authInfo = token.info
            user.title = unicode(res['name'])
            user.description = u'{} {}'.format(res['given_name'], res['family_name'])
            user.domain = u'Facebook'
            user.login = unicode(token.info['id_token'])
            user.secret = unicode(token.info['access_token'])
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
        uid = u"Twitter.{}".format(users.sequence)

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = list(found)[0]

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
        uid = u"Reddit.{}".format(users.sequence)

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = list(found)[0]

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
        uid = u"GitHub.{}".format(users.sequence)

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = list(found)[0]

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
        uid = u"Instagram.{}".format(users.sequence)

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = list(found)[0]

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
        uid = u"Mixer.{}".format(users.sequence)

        found = users.find(id=uid)
        if len(found)==0:
            user = users.new(id=uid)
        else:
            user = list(found)[0]

        user.authInfo = token.info
        user.domain = u'Mixer'
        user.login = token.info['id_token']
        user.secret = token.info['access_token']
        return user


