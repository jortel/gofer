# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# amqp://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from unittest import TestCase

from mock import Mock

from gofer.messaging.adapter.factory import Loader, __package__ as PACKAGE
from gofer.messaging.adapter.factory import Adapter
from gofer.messaging.adapter.factory import AdapterError, AdapterNotFound, NoAdaptersLoaded
from gofer.messaging.adapter.url import URL
from gofer.messaging.model import ModelError

from gofer.devel import patch


class TestExceptions(TestCase):

    def test_adapter_error(self):
        self.assertTrue(isinstance(AdapterError(), ModelError))

    def test_no_adapters_loaded(self):
        exception = NoAdaptersLoaded()
        self.assertTrue(isinstance(exception, AdapterError))
        self.assertEqual(str(exception), NoAdaptersLoaded.DESCRIPTION)

    def test_adapter_not_found(self):
        name = 'qpid'
        exception = AdapterNotFound(name)
        self.assertTrue(isinstance(exception, AdapterError))
        self.assertEqual(str(exception), AdapterNotFound.DESCRIPTION % name)


class TestLoader(TestCase):

    PACKAGE = 'gofer.testing'
    FILE = 'test-factory.py'

    def test_construction(self):
        ldr = Loader()
        self.assertEqual(ldr.list, [])
        self.assertEqual(ldr.catalog, {})

    @patch('builtins.__import__')
    @patch('os.path.isdir')
    @patch('os.listdir')
    def test__load(self, _listdir, _isdir, _import):
        listing = [
            ['p1', Mock(__name__='p1', PROVIDES=['A', 'B'])],
            ['p2', Mock(__name__='p2', PROVIDES=['C', 'D'])],
            ['p3', Mock(__name__='p3', PROVIDES=['E', 'F'])],
            ['p4', Mock(__name__='p4', PROVIDES=['G', 'H'])],
            ['p5', AttributeError],
            ['p6', ImportError],
            ['f1', None],
        ]

        loaded = self._loaded(listing)

        def isdir(p):
            return os.path.basename(p).startswith('p')

        _listdir.return_value = [p[0] for p in listing]
        _isdir.side_effect = isdir
        _import.side_effect = [p[1] for p in listing]
        _list, catalog = Loader._load()
        self.assertEqual(_list, loaded[0])
        self.assertEqual(catalog, loaded[1])

    def _loaded(self, listing):
        _list = []
        catalog = {}
        for name, pkg in listing:
            if not name.startswith('p'):
                continue
            if not isinstance(pkg, Mock):
                continue
            _list.append(pkg)
            catalog[name] = pkg
            catalog['.'.join((PACKAGE, name))] = pkg
            for c in pkg.PROVIDES:
                catalog[c] = pkg
        return _list, catalog

    @patch('gofer.messaging.adapter.factory.Loader._load')
    def test_load(self, _load):
        _load.return_value = ([], {})
        ldr = Loader()
        _list, catalog = ldr.load()
        _load.assert_called_with()
        self.assertEqual(_list, _load.return_value[0])
        self.assertEqual(catalog, _load.return_value[1])
        self.assertEqual(ldr.list, _load.return_value[0])
        self.assertEqual(ldr.catalog, _load.return_value[1])

    @patch('gofer.messaging.adapter.factory.Loader._load')
    def test_already_loaded(self, _load):
        ldr = Loader()
        ldr.list = [1, 2]
        ldr.catalog = {'A': 1, 'B': 2}
        _list, catalog = ldr.load()
        self.assertFalse(_load.called)
        self.assertEqual(_list, ldr.list)
        self.assertEqual(catalog, ldr.catalog)


class AdapterTest(TestCase):

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_bind(self, _load):
        name = 'qpid'
        adapter = Mock()
        url = URL('redhat.com')
        _load.return_value = [adapter], {name: adapter}

        Adapter.bind(str(url), name)

        _load.assert_called_with()
        self.assertEqual(Adapter.bindings, {url.canonical: adapter})

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_bind_not_found(self, _load):
        _load.return_value = [Mock()], {'A': Mock()}
        self.assertRaises(AdapterNotFound, Adapter.bind, '', '')

    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_bind_nothing_loaded(self, _load):
        _load.return_value = [], {}
        self.assertRaises(NoAdaptersLoaded, Adapter.bind, '', '')

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find(self, _load):
        name = 'A'
        url = '%s+amqp://redhat.com' % name
        adapter = Mock()
        _load.return_value = [adapter], {name: adapter}

        p = Adapter.find(url)

        _load.assert_called_with()
        self.assertEqual(p, adapter)

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_with_binding(self, _load):
        name = 'A'
        url = 'amqp://redhat.com'
        adapter = Mock()
        _load.return_value = [adapter], {name: adapter}

        Adapter.bind(url, name)
        p = Adapter.find(url)

        _load.assert_called_with()
        self.assertEqual(p, adapter)

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_not_matched(self, _load):
        url = 'amqp://redhat.com'
        _list = [1, 2, 3]
        catalog = {
            'C': _list[0],
            'B': _list[1],
            'A': _list[2]
        }
        _load.return_value = _list, catalog
        self.assertRaises(AdapterNotFound, Adapter.find, url)

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_without_url(self, _load):
        _list = [1, 2, 3]
        catalog = {
            'C': _list[0],
            'B': _list[1],
            'A': _list[2]
        }
        _load.return_value = _list, catalog
        p = Adapter.find('')
        self.assertEqual(p, _list[0])

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_nothing_loaded(self, _load):
        _load.return_value = [], {}
        self.assertRaises(NoAdaptersLoaded, Adapter.find, '')
