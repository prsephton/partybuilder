import grok
from datetime import datetime as dt
from datetime import timedelta as td
from interfaces import IBuilderApp, IItemCache, ISkinCache, IItemStatsCache, ITraitsCache, ISkillsCache

class Cached(object):
    item = None
    expires = None
    
    def __init__(self, item, lifetime=None):
        if lifetime is None: lifetime = td(minutes=120)
        self.item = item
        self.expires = dt.now() + lifetime

    def value(self):
        if self.expires < dt.now(): return None
        return self.item

class Cache(grok.Container):
        
    def __getitem__(self, key):
        key = str(key)
        if key in self.keys():
            item = grok.Container.__getitem__(self, key)
            value = item.value()
            if value is not None:
                return value
            del self[key]
            
    def __setitem__(self, key, value):
        key = str(key)
        if key not in self.keys():
            grok.Container.__setitem__(self, key, Cached(value))        


class DeleteCache(grok.View):
    grok.context(Cache)
    grok.name('delete')
    grok.require('zope.Public')
    
    def render(self):
        dset = [k for k in self.context.keys()]
        for d in dset:
            del self.context[d]
        return 'Deleted cache'
        

class ItemCache(Cache):
    grok.implements(IItemCache)


class AppItemCache(grok.Adapter):
    grok.context(IBuilderApp)
    grok.implements(IItemCache)
    
    def __new__(self, app):
        if 'item_cache' in app.keys():
            return app['item_cache']
        cache = app['item_cache'] = ItemCache()
        return cache
    

class SkinCache(Cache):
    grok.implements(ISkinCache)

        
class AppSkinCache(grok.Adapter):
    grok.context(IBuilderApp)
    grok.implements(ISkinCache)
    
    def __new__(self, app):
        if 'skin_cache' in app.keys():
#             del app['skin_cache']
            return app['skin_cache']
        cache = app['skin_cache'] = SkinCache()
        return cache

class ItemStatsCache(Cache):
    grok.implements(IItemStatsCache)

        
class AppItemStatsCache(grok.Adapter):
    grok.context(IBuilderApp)
    grok.implements(IItemStatsCache)
    
    def __new__(self, app):
        if 'itemstats_cache' in app.keys():
#            del app['itemstats_cache']
            return app['itemstats_cache']
        cache = app['itemstats_cache'] = ItemStatsCache()
        return cache
    
class TraitsCache(Cache):
    grok.implements(ITraitsCache)

        
class AppTraitsCache(grok.Adapter):
    grok.context(IBuilderApp)
    grok.implements(ITraitsCache)
    
    def __new__(self, app):
        if 'traits_cache' in app.keys():
            return app['traits_cache']
        cache = app['traits_cache'] = TraitsCache()
        return cache
    
    
class SkillsCache(Cache):
    grok.implements(ISkillsCache)

        
class AppSkillsCache(grok.Adapter):
    grok.context(IBuilderApp)
    grok.implements(ISkillsCache)
    
    def __new__(self, app):
        if 'skills_cache' in app.keys():
            return app['skills_cache']
        cache = app['skills_cache'] = SkillsCache()
        return cache
    

    

