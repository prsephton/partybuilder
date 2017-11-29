import grok

from partybuilder import resource

class Partybuilder(grok.Application, grok.Container):
    pass

class Index(grok.View):
    def update(self):
        resource.style.need()
