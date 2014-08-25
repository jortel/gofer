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

import os

from unittest import TestCase

from mock import patch, call, Mock

from gofer.messaging.provider.factory import Loader, REQUIRED
from gofer.messaging.provider.factory import Provider
from gofer.messaging.provider.factory import ProviderError, ProviderNotFound, NoProvidersLoaded
from gofer.messaging.provider.url import URL


class TestProvider(object):

    @staticmethod
    def provider(provides):
        provider = TestProvider()
        setattr(provider, 'PROVIDES', provides)
        return provider


class TestExceptions(TestCase):

    def testProviderError(self):
        self.assertTrue(isinstance(ProviderError(), Exception))

    def testNoProvidersLoaded(self):
        exception = NoProvidersLoaded()
        self.assertTrue(isinstance(exception, ProviderError))
        self.assertEqual(exception.message, NoProvidersLoaded.DESCRIPTION)

    def testProviderNotFound(self):
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
    @patch('gofer.messaging.provider.factory.__file__', FILE)
    @patch('gofer.messaging.provider.factory.PACKAGE', PACKAGE)
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('os.path.dirname')
    def test__load(self, _dirname, _isdir, _listdir, _import):
        _dir = 'test'
        providers = [
            ['A', True, TestProvider.provider(['AA', 'TEST-A'])],
            ['B', True, TestProvider.provider(['BB', 'TEST-B'])],
            ['D', True, TestProvider.provider(['DD', 'TEST-D'])],
            ['E', False, TestProvider.provider([])],
            ['F', True, AttributeError()],
            ['G', True, ImportError()],
        ]

        _dirname.return_value = _dir
        _listdir.return_value = [p[0] for p in providers]
        _isdir.side_effect = [p[1] for p in providers]
        _import.side_effect = [p[2] for p in providers if p[1]]

        loaded = Loader._load()
        _dirname.assert_called_once_with(TestLoader.FILE)
        _listdir.assert_called_once_with(_dir)
        self.assertEqual(
            _isdir.call_args_list,
            [call(os.path.join(_dir, p[0])) for p in providers])
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
            if not p[1]:
                continue
            pkg = '.'.join((TestLoader.PACKAGE, p[0]))
            calls.append(call(pkg, {}, {}, REQUIRED))
        return calls

    def _valid(self, p):
        return not self._invalid(p)

    def _invalid(self, p):
        if not p[1]:
            # not a directory
            return True
        if isinstance(p[2], Exception):
            return True
        return False

    def _load(self, providers):
        loaded = {}
        for p in providers:
            if self._invalid(p):
                continue
            loaded[p[0]] = p[2]
            pkg = '.'.join([TestLoader.PACKAGE, p[0]])
            loaded[pkg] = p[2]
            for capability in p[2].PROVIDES:
                loaded[capability] = p[2]
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