import grok
from zope.schema import Int, TextLine
from zope.formlib.interfaces import IInputWidget
from zope.publisher.browser import IBrowserRequest
from zope.formlib.widget import SimpleInputWidget

#________________________________________________________________
# A hidden int widget
class HiddenInt(Int):
    ''' Render as text, but retrieves the widget data as an int '''

#________________________________________________________________
class HiddenIntWidget(SimpleInputWidget):
    ''' Our hidden text widget is easily derived from SimpleInputWidget.  We override
        the __call__ to render as a hidden input
    '''
    def _toFieldValue(self, aInput):
        if aInput is None or len(aInput)==0:
            return None
        return int(aInput)

    def __call__(self):
        return self.hidden()

#________________________________________________________________
class HiddenIntAdapter(grok.MultiAdapter):
    '''  Define an adapter for our schema field which selects our hidden text widget
    '''
    grok.adapts(HiddenInt, IBrowserRequest)
    grok.implements(IInputWidget)

    def __new__(self, field, request):
        return HiddenIntWidget(field, request)

#________________________________________________________________
class HiddenText(TextLine):
    ''' We register an adapter for this new schema field which renders a hidden text field '''

#________________________________________________________________
class HiddenTextWidget(SimpleInputWidget):
    ''' Our hidden text widget is easily derived from SimpleInputWidget.  We override
        the __call__ to render as a hidden input
    '''
    def _toFieldValue(self, aInput):
        return unicode(aInput)

    def __call__(self):
        return self.hidden()

#________________________________________________________________
class HiddenTextAdapter(grok.MultiAdapter):
    '''  Define an adapter for our schema field which selects our hidden text widget
    '''
    grok.adapts(HiddenText, IBrowserRequest)
    grok.implements(IInputWidget)

    def __new__(self, field, request):
        return HiddenTextWidget(field, request)
