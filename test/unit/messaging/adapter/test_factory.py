# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch, call, Mock

from gofer.config import get_bool
from gofer.messaging.adapter.factory import Loader, REQUIRED
from gofer.messaging.adapter.factory import Adapter
from gofer.messaging.adapter.factory import AdapterError, AdapterNotFound, NoAdaptersLoaded
from gofer.messaging.adapter.url import URL
from gofer.messaging.model import ModelError


class TestDescriptor(object):

    def __init__(self, path, enabled, package, provides):
        self.main = Mock(path=path, enabled=enabled, package=package)
        self.provides = provides


class TestExceptions(TestCase):

    def test_adapter_error(self):
        self.assertTrue(isinstance(AdapterError(), ModelError))

    def test_no_adapters_loaded(self):
        exception = NoAdaptersLoaded()
        self.assertTrue(isinstance(exception, AdapterError))
        self.assertEqual(exception.message, NoAdaptersLoaded.DESCRIPTION)

    def test_adapter_not_found(self):
        name = 'qpid'
        exception = AdapterNotFound(name)
        self.assertTrue(isinstance(exception, AdapterError))
        self.assertEqual(exception.message, AdapterNotFound.DESCRIPTION % name)


class TestLoader(TestCase):

    PACKAGE = 'gofer.testing'
    FILE = 'test-factory.py'

    def test_construction(self):
        ldr = Loader()
        self.assertEqual(ldr.list, [])
        self.assertEqual(ldr.catalog, {})

    @patch('__builtin__.__import__')
    @patch('gofer.messaging.adapter.descriptor.Descriptor.load')
    def test__load(self, _load, _import):
        adapters = [
            [TestDescriptor('path-A', '1', 'p1', ['AA', 'TEST-A']), Mock(__name__='p1')],
            [TestDescriptor('path-B', '1', 'p2', ['BB', 'TEST-B']), Mock(__name__='p2')],
            [TestDescriptor('path-C', '1', 'p3', ['CC', 'TEST-C']), Mock(__name__='p3')],
            [TestDescriptor('path-D', '0', 'p4', ['DD', 'TEST-E']), Mock(__name__='p4')],
            [TestDescriptor('path-E', '1', 'p5', ['EE', 'TEST-E']), AttributeError()],
            [TestDescriptor('path-E', '1', 'p6', ['FF', 'TEST-F']), ImportError()],
        ]

        _load.return_value = [p[0] for p in adapters]
        _import.side_effect = [p[1] for p in adapters if get_bool(p[0].main.enabled)]

        _list, catalog = Loader._load(Loader.PATH)
        self.assertEqual(_import.call_args_list, self._import_calls(adapters))
        self.assertEqual(_list, self._load(adapters)[0])
        self.assertEqual(catalog, self._load(adapters)[1])

    @patch('gofer.messaging.adapter.factory.Loader._load')
    def test_load(self, _load):
        _load.return_value = ([], {})
        ldr = Loader()
        _list, catalog = ldr.load()
        _load.assert_called_with(Loader.PATH)
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

    def _import_calls(self, adapters):
        calls = []
        for p in adapters:
            if not get_bool(p[0].main.enabled):
                continue
            pkg = p[0].main.package
            calls.append(call(pkg, {}, {}, REQUIRED))
        return calls

    def _skip(self, p):
        if not get_bool(p[0].main.enabled):
            return True
        if isinstance(p[1], Exception):
            return True
        return False

    def _load(self, adapters):
        _list = []
        catalog = {}
        for p in adapters:
            if self._skip(p):
                continue
            _list.append(p[1])
            catalog[p[0].main.package] = p[1]
            catalog[p[1].__name__] = p[1]
            for capability in p[0].provides:
                catalog[capability] = p[1]
        return _list, catalog


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
        self.assertEqual(Adapter.bindings, {url.simple(): adapter})

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
        url = '%s+http://redhat.com' % name
        adapter = Mock()
        _load.return_value = [adapter], {name: adapter}

        p = Adapter.find(url)

        _load.assert_called_with()
        self.assertEqual(p, adapter)

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_with_binding(self, _load):
        name = 'A'
        url = 'http://redhat.com'
        adapter = Mock()
        _load.return_value = [adapter], {name: adapter}

        Adapter.bind(url, name)
        p = Adapter.find(url)

        _load.assert_called_with()
        self.assertEqual(p, adapter)

    @patch('gofer.messaging.adapter.factory.Adapter.bindings', {})
    @patch('gofer.messaging.adapter.factory.Loader.load')
    def test_find_not_matched(self, _load):
        url = 'http://redhat.com'
        _list = [1, 2, 3]
        catalog = {
            'C': _list[0],
            'B': _list[1],
            'A': _list[2]
        }
        _load.return_value = _list, catalog
        p = Adapter.find(url)
        self.assertEqual(p, _list[0])

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
