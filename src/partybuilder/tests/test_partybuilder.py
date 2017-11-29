import unittest

from zope.component import queryMultiAdapter
from zope.publisher.browser import TestRequest

from zope.fanstatic.testing import ZopeFanstaticBrowserLayer

import partybuilder.tests
from partybuilder.builder import Partybuilder

# In this file we create a unittest, a functional unittest.

class MyTestCase(unittest.TestCase):

    def test_foo(self):
        self.assertEqual(1, 1)

browser_layer = ZopeFanstaticBrowserLayer(partybuilder.tests)

class MyFunctionalTestCase(unittest.TestCase):

    layer = browser_layer

    def test_foo(self):
        index = queryMultiAdapter((Partybuilder(), TestRequest()), name='index')
        self.assertNotEqual(index, None)

        # There is no view called 'index2'
        index2 = queryMultiAdapter((Partybuilder(), TestRequest()), name='index2')
        self.assertEqual(index2, None)

