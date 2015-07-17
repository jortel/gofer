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

from mock import patch, Mock

from gofer.agent.rmi import Scheduler
from gofer.messaging import Document


class TestScheduler(TestCase):

    @patch('threading.Thread.setDaemon')
    @patch('gofer.agent.rmi.Pending')
    @patch('gofer.agent.rmi.Builtin')
    def test_init(self, builtin, pending, set_daemon):
        plugin = Mock(stream='1234')
        scheduler = Scheduler(plugin)
        pending.assert_called_once_with(plugin.stream)
        builtin.assert_called_once_with(plugin)
        set_daemon.assert_called_with(True)
        self.assertEqual(scheduler.plugin, plugin)
        self.assertEqual(scheduler.pending, pending.return_value)
        self.assertEqual(scheduler.builtin, builtin.return_value)

    @patch('gofer.common.Thread.aborted')
    @patch('gofer.agent.rmi.Scheduler.select_plugin')
    @patch('gofer.agent.rmi.Task')
    @patch('gofer.agent.rmi.Pending')
    @patch('gofer.agent.rmi.Builtin')
    @patch('threading.Thread.setDaemon', Mock())
    def test_run(self, builtin, pending, task, select_plugin, aborted):
        plugin = Mock()
        task_list = [
            Mock(name='task-1'),
            Mock(name='task-2'),
        ]
        request_list = [
            Document(sn=1),
            Document(sn=2),
        ]
        task.side_effect = task_list
        aborted.side_effect = [False, False, True]
        pending.return_value.get.side_effect = request_list
        builtin.return_value.provides.side_effect = [True, False]
        select_plugin.side_effect = [builtin.return_value, plugin]

        # test
        scheduler = Scheduler(plugin)
        scheduler.run()

        # validation
        builtin.return_value.pool.run.assert_called_once_with(task_list[0])
        plugin.pool.run.assert_called_once_with(task_list[1])
        self.assertEqual(
            select_plugin.call_args_list,
            [
                ((request_list[0],), {}),
                ((request_list[1],), {}),
            ])
        self.assertEqual(
            task.call_args_list,
            [
                ((builtin.return_value, request_list[0], pending.return_value.commit), {}),
                ((plugin, request_list[1], pending.return_value.commit), {})
            ])

    @patch('gofer.agent.rmi.Pending')
    @patch('gofer.agent.rmi.Scheduler.select_plugin')
    @patch('gofer.common.Thread.aborted')
    @patch('gofer.agent.rmi.Task', Mock())
    @patch('gofer.agent.rmi.Builtin', Mock())
    @patch('threading.Thread.setDaemon', Mock())
    def test_run_raised(self, aborted, select_plugin, pending):
        plugin = Mock()
        sn = 1234
        pending.return_value.get.return_value = Document(sn=sn)
        select_plugin.side_effect = ValueError
        aborted.side_effect = [False, True]

        # test
        scheduler = Scheduler(plugin)
        scheduler.run()

        # validation
        pending.return_value.commit.assert_called_once_with(sn)

    @patch('gofer.agent.rmi.Builtin')
    @patch('gofer.agent.rmi.Pending', Mock())
    @patch('threading.Thread.setDaemon', Mock())
    def test_select_plugin(self, builtin):
        plugin = Mock()
        request = Document(request={'classname': 'A'})
        scheduler = Scheduler(plugin)
        # find builtin
        builtin.return_value.provides.return_value = True
        selected = scheduler.select_plugin(request)
        self.assertEqual(selected, builtin.return_value)
        # find plugin
        builtin.return_value.provides.return_value = False
        selected = scheduler.select_plugin(request)
        self.assertEqual(selected, plugin)
        self.assertEqual(
            builtin.return_value.provides.call_args_list,
            [
                (('A',), {}),
                (('A',), {})
            ])

    @patch('gofer.agent.rmi.Pending')
    @patch('gofer.agent.rmi.Builtin', Mock())
    @patch('threading.Thread.setDaemon', Mock())
    def test_add(self, pending):
        plugin = Mock()
        request = Mock()
        scheduler = Scheduler(plugin)
        scheduler.add(request)
        pending.return_value.put.assert_called_once_with(request)

    @patch('gofer.agent.rmi.Builtin')
    @patch('gofer.common.Thread.abort')
    @patch('gofer.agent.rmi.Pending', Mock())
    @patch('threading.Thread.setDaemon', Mock())
    def test_shutdown(self, abort, builtin):
        plugin = Mock()
        scheduler = Scheduler(plugin)
        scheduler.shutdown()
        builtin.return_value.shutdown.assert_called_once_with()
        abort.assert_called_once_with()
