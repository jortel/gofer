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

from mock import patch, Mock, ANY

from gofer.agent.plugin import attach
from gofer.agent.plugin import Container, Hook


class TestAttach(TestCase):

    def test_call(self):
        fn = Mock()
        pool = Mock(queue=[])
        pool.run.side_effect = pool.queue.append
        plugin = Mock(url=1, uuid=2, pool=pool)
        _fn = attach(fn)
        _fn(plugin)
        call = pool.queue[0]
        call()
        plugin.pool.run.assert_called_once_with(ANY)
        fn.assert_called_once_with(plugin)

    def test_not_called(self):
        fn = Mock()
        pool = Mock(queue=[])
        pool.run.side_effect = pool.queue.append
        plugin = Mock(url=0, uuid=2, pool=pool)
        _fn = attach(fn)
        _fn(plugin)
        call = pool.queue[0]
        call()
        plugin.pool.run.assert_called_once_with(ANY)
        self.assertFalse(fn.called)


class TestContainer(TestCase):

    def test_init(self):
        cnt = Container()
        self.assertEqual(cnt.plugins, {})

    def test_add(self):
        plugin = Mock()
        cnt = Container()
        cnt.add(plugin)
        self.assertEqual(
            cnt.plugins,
            {
                plugin.name: plugin,
                plugin.path: plugin
            })

    def test_add_with_names(self):
        plugin = Mock()
        names = ['A', 'B']
        cnt = Container()
        cnt.add(plugin, *names)
        self.assertEqual(
            cnt.plugins,
            {
                plugin.path: plugin,
                names[0]: plugin,
                names[1]: plugin
            })

    def test_delete(self):
        plugin = Mock()
        plugin2 = Mock()
        names = ['A', 'B']
        cnt = Container()
        cnt.add(plugin, *names)
        cnt.add(plugin2)
        cnt.delete(plugin)
        self.assertEqual(
            cnt.plugins,
            {
                plugin2.name: plugin2,
                plugin2.path: plugin2
            })

    def test_find(self):
        plugin = Mock()
        cnt = Container()
        cnt.add(plugin)
        p = cnt.find(plugin.name)
        self.assertEqual(p, plugin)
        p = cnt.find('joe')
        self.assertEqual(p, None)

    def test_call(self):
        cnt = Container()
        cnt.plugins = {'A': 1, 'B': 2, 'C': 2}
        plugins = cnt.all()
        self.assertEqual(plugins, [1, 2])


class TestHook(TestCase):

    def test_init(self):
        h = Hook()
        self.assertEqual(h.load, [])
        self.assertEqual(h.unload, [])

    def test_loaded(self):
        h = Hook()
        h.load = [Mock(), Mock()]
        h.loaded()
        for fn in h.load:
            fn.assert_called_once_with()

    def test_unloaded(self):
        h = Hook()
        h.unload = [Mock(), Mock()]
        h.unloaded()
        for fn in h.unload:
            fn.assert_called_once_with()
