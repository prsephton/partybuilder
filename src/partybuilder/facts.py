#________________________________________________________________________________________
#  Represent facts as per GW2 API definition

import grok
from interfaces import IFact

class Fact(object):    
    def __init__(self, fact, attribs):
        for a in ['type', 'text', 'icon']:
            if a in fact.keys(): setattr(self, a, fact[a])
        for a in attribs:
            if a in fact.keys(): setattr(self, a, fact[a])

class Adjust(Fact):    
    def __init__(self, fact):
        super(Adjust, self).__init__(fact, ['value', 'target'])
        
class Buff(Fact):    
    def __init__(self, fact):
        super(Buff, self).__init__(fact, ['duration', 'status', 'description', 'apply_count'])

class ComboField(Fact):    
    def __init__(self, fact):
        super(ComboField, self).__init__(fact, ['field_type'])

class ComboFinisher(Fact):    
    def __init__(self, fact):
        super(ComboFinisher, self).__init__(fact, ['percent', 'finisher_type'])

class Damage(Fact):    
    def __init__(self, fact):
        super(Damage, self).__init__(fact, ['hit_count', 'dmg_multiplier'])

class Distance(Fact):    
    def __init__(self, fact):
        super(Distance, self).__init__(fact, ['distance'])

class Duration(Fact):    
    def __init__(self, fact):
        super(Duration, self).__init__(fact, ['duration'])

class Healing(Fact):    
    def __init__(self, fact):
        super(Healing, self).__init__(fact, ['hit_count'])

class HealingAdjust(Fact):    
    def __init__(self, fact):
        super(HealingAdjust, self).__init__(fact, ['hit_count'])

class NoData(Fact):    
    def __init__(self, fact):
        super(NoData, self).__init__(fact, [])

class Number(Fact):    
    def __init__(self, fact):
        super(Number, self).__init__(fact, ['value'])

class Percent(Fact):    
    def __init__(self, fact):
        super(Percent, self).__init__(fact, ['percent'])

class Prefix(Fact):    
    def __init__(self, fact):
        super(Prefix, self).__init__(fact, ['status', 'description'])

class PrefixedBuff(Fact):    
    def __init__(self, fact):
        super(PrefixedBuff, self).__init__(fact, ['duration', 'status', 'description', 'apply_count'])
        
class Radius(Fact):    
    def __init__(self, fact):
        super(Radius, self).__init__(fact, ['distance'])

class Range(Fact):    
    def __init__(self, fact):
        super(Range, self).__init__(fact, ['value'])

class Recharge(Fact):    
    def __init__(self, fact):
        super(Recharge, self).__init__(fact, ['value'])

class Time(Fact):    
    def __init__(self, fact):
        super(Time, self).__init__(fact, ['duration'])

class Unblockable(Fact):    
    def __init__(self, fact):
        super(Unblockable, self).__init__(fact, [])


class FactFactory(grok.GlobalUtility):
    ''' Produces facts '''
    grok.implements(IFact)
    
    def __call__(self, factData):
        if type(factData) is list:
            factFactory = FactFactory()
            ret = [factFactory(i) for i in factData]
            return [fact for fact in ret if fact]
        if type(factData) is dict:
            if 'type' in factData:
                ftype = factData['type']
                try:
                    if ftype == 'Adjust':        return Adjust(factData)
                    if ftype == 'Buff':          return Buff(factData)
                    if ftype == 'ComboField':    return ComboField(factData)
                    if ftype == 'ComboFinisher': return ComboFinisher(factData)
                    if ftype == 'Damage':        return Damage(factData)
                    if ftype == 'Distance':      return Distance(factData)
                    if ftype == 'Duration':      return Duration(factData)
                    if ftype == 'Healing':       return Healing(factData)
                    if ftype == 'HealingAdjust': return HealingAdjust(factData)
                    if ftype == 'NoData':        return NoData(factData)
                    if ftype == 'Number':        return Number(factData)
                    if ftype == 'Percent':       return Percent(factData)
                    if ftype == 'PrefixedBuff':  return PrefixedBuff(factData)
                    if ftype == 'Radius':        return Radius(factData)
                    if ftype == 'Range':         return Range(factData)
                    if ftype == 'Recharge':      return Recharge(factData)
                    if ftype == 'Time':          return Time(factData)
                    if ftype == 'Unblockable':   return Unblockable(factData)
                except:
                    return NoData(factData)

