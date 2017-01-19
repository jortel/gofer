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

from gofer.common import Singleton
from gofer.agent.plugin import attach
from gofer.agent.plugin import Container, Plugin


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

    def setUp(self):
        Singleton._inst.clear()

    def tearDown(self):
        Singleton._inst.clear()

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


class TestPlugin(TestCase):

    @patch('gofer.agent.plugin.Delegate')
    @patch('gofer.agent.plugin.Scheduler')
    @patch('gofer.agent.plugin.Whiteboard')
    @patch('gofer.agent.plugin.Dispatcher')
    @patch('gofer.agent.plugin.ThreadPool')
    def test_init(self, pool, dispatcher, whiteboard, scheduler, delegate):
        threads = 4
        descriptor = Mock(main=Mock(threads=threads))
        path = '/tmp/path'

        # test
        plugin = Plugin(descriptor, path)

        # validation
        pool.assert_called_once_with(threads)
        dispatcher.assert_called_once_with()
        scheduler.assert_called_once_with(plugin)
        delegate.assert_called_once_with()
        self.assertEqual(plugin.descriptor, descriptor)
        self.assertEqual(plugin.path, path)
        self.assertEqual(plugin.pool, pool.return_value)
        self.assertEqual(plugin.impl, None)
        self.assertEqual(plugin.actions, [])
        self.assertEqual(plugin.dispatcher, dispatcher.return_value)
        self.assertEqual(plugin.whiteboard, whiteboard.return_value)
        self.assertEqual(plugin.scheduler, scheduler.return_value)
        self.assertEqual(plugin.delegate, delegate.return_value)
        self.assertEqual(plugin.authenticator, None)
        self.assertEqual(plugin.consumer, None)

    @patch('gofer.agent.plugin.BrokerModel')
    @patch('gofer.agent.plugin.Connector')
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    def test_properties(self, connector, model):
        descriptor = Mock(
            main=Mock(
                enabled='1',
                threads=4,
                latency=0.5,
                forward='a, b, c',
                accept='d, e, f'),
            messaging=Mock(
                uuid='x99',
                url='amqp://localhost')
        )
        plugin = Plugin(descriptor, '')
        plugin.scheduler = Mock()
        # name
        self.assertEqual(plugin.name, descriptor.main.name)
        # cfg
        self.assertEqual(plugin.cfg, descriptor)
        # uuid
        self.assertEqual(plugin.uuid, descriptor.messaging.uuid)
        # latency
        self.assertEqual(plugin.latency, descriptor.main.latency)
        # url
        self.assertEqual(plugin.url, descriptor.messaging.url)
        # enabled
        self.assertTrue(plugin.enabled)
        # connector
        self.assertEqual(plugin.connector, connector.return_value)
        connector.assert_called_once_with(descriptor.messaging.url)
        # queue
        self.assertEqual(plugin.node, model.return_value.node)
        model.assert_called_once_with(plugin)
        # forward
        _list = descriptor.main.forward
        self.assertEqual(
            plugin.forward,
            set([p.strip() for p in _list.split(',')]))
        # accept
        _list = descriptor.main.accept
        self.assertEqual(
            plugin.accept,
            set([p.strip() for p in _list.split(',')]))
        # is_started
        self.assertEqual(plugin.is_started, plugin.scheduler.isAlive.return_value)

    @patch('gofer.agent.plugin.Scheduler')
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    def test_start(self, scheduler):
        descriptor = Mock(main=Mock(threads=4))
        scheduler.return_value.isAlive.return_value = False

        # test
        plugin = Plugin(descriptor, '')
        plugin.attach = Mock()
        plugin.start()

        # validation
        plugin.attach.assert_called_once_with()
        scheduler.return_value.start.assert_called_once_with()

    @patch('gofer.agent.plugin.Scheduler')
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    def test_start_already_started(self, scheduler):
        descriptor = Mock(main=Mock(threads=4))
        scheduler.return_value.isAlive.return_value = True

        # test
        plugin = Plugin(descriptor, '')
        plugin.attach = Mock()
        plugin.start()

        # validation
        self.assertFalse(plugin.attach.called)
        self.assertFalse(scheduler.return_value.start.called)

    @patch('gofer.agent.plugin.Scheduler')
    @patch('gofer.agent.plugin.ThreadPool')
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_shutdown(self, pool, scheduler):
        descriptor = Mock(main=Mock(threads=4))
        scheduler.return_value.isAlive.return_value = True

        # test
        plugin = Plugin(descriptor, '')
        plugin.detach = Mock()
        plugin.shutdown(False)

        # validation
        plugin.detach.assert_called_once_with(False)
        scheduler.return_value.shutdown.assert_called_once_with()
        scheduler.return_value.join.assert_called_once_with()
        pool.return_value.shutdown.assert_called_once_with(hard=False)

    @patch('gofer.agent.plugin.Scheduler')
    @patch('gofer.agent.plugin.ThreadPool')
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_shutdown_not_running(self, pool, scheduler):
        descriptor = Mock(main=Mock(threads=4))
        scheduler.return_value.isAlive.return_value = False

        # test
        plugin = Plugin(descriptor, '')
        plugin.detach = Mock()
        plugin.shutdown(False)

        # validation
        self.assertFalse(plugin.detach.called)
        self.assertFalse(scheduler.return_value.shutdown.called)
        self.assertFalse(scheduler.return_value.join.called)
        self.assertFalse(pool.return_value.shutdown.called)

    @patch('gofer.agent.plugin.Connector')
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_refresh(self, connector):
        url = 'amqp://localhost'
        descriptor = Mock(
            main=Mock(
                enabled='1',
                threads=4),
            messaging=Mock(
                uuid='x99',
                url='amqp://localhost',
                cacert='ca',
                clientkey='key',
                clientcert='crt',
                heartbeat='8')
        )

        # test
        plugin = Plugin(descriptor, '')
        plugin.refresh()

        # validation
        connector.assert_called_once_with(descriptor.messaging.url)
        connector = connector.return_value
        connector.add.assert_called_once_with()
        self.assertEqual(connector.ssl.ca_certificate, descriptor.messaging.cacert)
        self.assertEqual(connector.ssl.client_key, descriptor.messaging.clientkey)
        self.assertEqual(connector.ssl.client_certificate, descriptor.messaging.clientcert)
        self.assertEqual(connector.ssl.host_validation, descriptor.messaging.host_validation)

    @patch('gofer.agent.plugin.Node')
    @patch('gofer.agent.plugin.RequestConsumer')
    @patch('gofer.agent.plugin.BrokerModel')
    @patch('gofer.agent.plugin.ThreadPool')
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_attach(self, pool, model, consumer, node):
        queue = 'test'
        descriptor = Mock(main=Mock(threads=4))
        pool.return_value.run.side_effect = lambda fn: fn()
        model.return_value.queue = queue

        # test
        plugin = Plugin(descriptor, '')
        plugin.authenticator = Mock()
        plugin.detach = Mock()
        plugin.refresh = Mock()
        plugin.attach()

        # validation
        plugin.detach.assert_called_once_with(False)
        model.assert_called_with(plugin)
        model.return_value.setup.assert_called_once_with()
        node.assert_called_once_with(queue)
        consumer.assert_called_once_with(node.return_value, plugin)
        consumer = consumer.return_value
        consumer.start.assert_called_once_with()
        self.assertEqual(consumer.authenticator, plugin.authenticator)
        self.assertEqual(plugin.consumer, consumer)

    @patch('gofer.agent.plugin.BrokerModel')
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_detach(self, model):
        descriptor = Mock(main=Mock(threads=4))
        consumer = Mock()

        # test
        plugin = Plugin(descriptor, '')
        plugin.consumer = consumer
        plugin.detach()

        # validation
        consumer.shutdown.assert_called_once_with()
        consumer.join.assert_called_once_with()
        model.assert_called_with(plugin)
        model = model.return_value
        model.teardown.assert_called_once_with()
        self.assertEqual(plugin.consumer, None)

    @patch('gofer.agent.plugin.BrokerModel')
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_detach_not_attached(self, model):
        descriptor = Mock(main=Mock(threads=4))

        # test
        plugin = Plugin(descriptor, '')
        plugin.detach()

        # validation
        self.assertFalse(model.called)

    @patch('gofer.agent.plugin.BrokerModel')
    @patch('gofer.agent.plugin.ThreadPool', Mock())
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_detach_no_teardown(self, model):
        descriptor = Mock(main=Mock(threads=4))
        consumer = Mock()

        # test
        plugin = Plugin(descriptor, '')
        plugin.consumer = consumer
        plugin.detach(teardown=False)

        # validation
        consumer.shutdown.assert_called_once_with()
        consumer.join.assert_called_once_with()
        self.assertFalse(model.teardown.called)
        self.assertEqual(plugin.consumer, None)

    @patch('gofer.agent.plugin.ThreadPool', Mock())
    @patch('gofer.agent.plugin.Scheduler', Mock())
    @patch('gofer.agent.plugin.Whiteboard', Mock())
    def test_provides(self):
        descriptor = Mock(main=Mock(threads=4))

        # test
        plugin = Plugin(descriptor, '')
        plugin.dispatcher = Mock()
        provides = plugin.provides('Dog')

        # validation
        self.assertEqual(provides, plugin.dispatcher.provides.return_value)
