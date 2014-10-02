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
from gofer.messaging.provider.factory import Loader, REQUIRED
from gofer.messaging.provider.factory import Provider
from gofer.messaging.provider.factory import ProviderError, ProviderNotFound, NoProvidersLoaded
from gofer.messaging.provider.url import URL


class TestDescriptor(object):

    def __init__(self, path, enabled, package, provides):
        self.main = Mock(path=path, enabled=enabled, package=package)
        self.provides = provides


class TestExceptions(TestCase):

    def test_provider_error(self):
        self.assertTrue(isinstance(ProviderError(), Exception))

    def test_no_providers_loaded(self):
        exception = NoProvidersLoaded()
        self.assertTrue(isinstance(exception, ProviderError))
        self.assertEqual(exception.message, NoProvidersLoaded.DESCRIPTION)

    def test_provider_not_found(self):
        name = 'qpid'
        exception = ProviderNotFound(name)
        self.assertTrue(isinstance(exception, ProviderError))
        self.assertEqual(exception.message, ProviderNotFound.DESCRIPTION % name)


class TestLoader(TestCase):

    PACKAGE = 'gofer.testing'
    FILE = 'test-factory.py'

    def test_construction(self):
        ldr = Loader()
        self.assertEqual(ldr.providers, {})

    @patch('__builtin__.__import__')
    @patch('gofer.messaging.provider.descriptor.Descriptor.load')
    def test__load(self, _load, _import):
        providers = [
            [TestDescriptor('path-A', '1', 'p1', ['AA', 'TEST-A']), Mock(__name__='p1')],
            [TestDescriptor('path-B', '1', 'p2', ['BB', 'TEST-B']), Mock(__name__='p2')],
            [TestDescriptor('path-C', '1', 'p3', ['CC', 'TEST-C']), Mock(__name__='p3')],
            [TestDescriptor('path-D', '0', 'p4', ['DD', 'TEST-E']), Mock(__name__='p4')],
            [TestDescriptor('path-E', '1', 'p5', ['EE', 'TEST-E']), AttributeError()],
            [TestDescriptor('path-E', '1', 'p6', ['FF', 'TEST-F']), ImportError()],
        ]

        _load.return_value = [p[0] for p in providers]
        _import.side_effect = [p[1] for p in providers if get_bool(p[0].main.enabled)]

        loaded = Loader._load()
        self.assertEqual(_import.call_args_list, self._import_calls(providers))
        self.assertEqual(loaded, self._load(providers))

    @patch('gofer.messaging.provider.factory.Loader._load')
    def test_load(self, _load):
        providers = Mock()
        _load.return_value = providers
        ldr = Loader()
        loaded = ldr.load()
        _load.assert_called_with()
        self.assertEqual(loaded, providers)

    @patch('gofer.messaging.provider.factory.Loader._load')
    def test_already_loaded(self, _load):
        providers = {'A': 1}
        ldr = Loader()
        ldr.providers = providers
        loaded = ldr.load()
        self.assertFalse(_load.called)
        self.assertEqual(loaded, providers)

    def _import_calls(self, providers):
        calls = []
        for p in providers:
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

    def _load(self, providers):
        loaded = {}
        for p in providers:
            if self._skip(p):
                continue
            loaded[p[0].main.package] = p[1]
            loaded[p[1].__name__] = p[1]
            for capability in p[0].provides:
                loaded[capability] = p[1]
        return loaded


class ProviderTest(TestCase):

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_bind(self, _load):
        name = 'qpid'
        provider = Mock()
        url = URL('redhat.com')
        _load.return_value = {name: provider}

        Provider.bind(str(url), name)

        _load.assert_called_with()
        self.assertEqual(Provider.urls, {url.simple(): provider})

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_bind_not_found(self, _load):
        _load.return_value = {'A': Mock()}
        self.assertRaises(ProviderNotFound, Provider.bind, '', '')

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_bind_nothing_loaded(self, _load):
        _load.return_value = {}
        self.assertRaises(NoProvidersLoaded, Provider.bind, '', '')

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_find(self, _load):
        name = 'A'
        url = '%s+http://redhat.com' % name
        provider = Mock()
        _load.return_value = {name: provider}

        p = Provider.find(url)

        _load.assert_called_with()
        self.assertEqual(p, provider)

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_find_with_binding(self, _load):
        name = 'A'
        url = 'http://redhat.com'
        provider = Mock()
        _load.return_value = {name: provider}

        Provider.bind(url, name)
        p = Provider.find(url)

        _load.assert_called_with()
        self.assertEqual(p, provider)

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_find_not_matched(self, _load):
        providers = {
            'C': Mock(),
            'B': Mock(),
            'A': Mock()
        }
        _load.return_value = providers
        p = Provider.find('')
        self.assertEqual(p, providers['A'])

    @patch('gofer.messaging.provider.factory.Loader.load')
    def test_find_nothing_loaded(self, _load):
        _load.return_value = {}
        self.assertRaises(NoProvidersLoaded, Provider.find, '')