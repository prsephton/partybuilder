from fanstatic import Library, Resource

library = Library('partybuilder', 'static')

bootstrap = Resource(library, 'bootstrap/bootstrap.css')
style = Resource(library, 'style.css')
jquery = Resource(library, 'jquery/jquery-3.2.1.min.js')
js_utils = Resource(library, 'utils.js', depends=[jquery])
