import grok
from interfaces import IOAuthPrincipal, ITokenRequest
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from zope import component


class SourcesVocabulary(grok.GlobalUtility):
    grok.implements(IVocabularyFactory)
    grok.name(u'oauth2.sources')

    def __call__(self, context):
        terms = []
        sm = component.getSiteManager(grok.getSite())
        adapters = sm.adapters.lookupAll((ITokenRequest,), IOAuthPrincipal)
        for name, _a in adapters:
            value  = name
            token  = str(name)
            title  = name
            terms.append(SimpleVocabulary.createTerm(value,token,title))
        return SimpleVocabulary(terms)
