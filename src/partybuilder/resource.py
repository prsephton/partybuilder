from fanstatic import Library, Resource

library = Library('partybuilder', 'static')

bootstrap = Resource(library, 'bootstrap/bootstrap.css')
style = Resource(library, 'style.css')
