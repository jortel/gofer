#
# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from unittest import TestCase

from mock import patch, Mock

from gofer.rmi.model.child import Progress, Call, ParentMonitor
from gofer.rmi.model import protocol
from gofer.mp import Pipe, PipeBroken


MODULE = 'gofer.rmi.model.child'


class TestProgress(TestCase):

    def test_report(self):
        pipe = Pipe()
        p = Progress(pipe.writer)
        p.total = 1
        p.completed = 2
        p.details = 'hello'

        # test
        p.report()

        # validation
        reply = protocol.Reply.read(pipe.reader)
        self.assertEqual(reply.code, protocol.Progress.CODE)
        self.assertEqual(reply.payload.total, p.total)
        self.assertEqual(reply.payload.completed, p.completed)
        self.assertEqual(reply.payload.details, p.details)


class TestCall(TestCase):

    @patch(MODULE + '.ParentMonitor')
    @patch(MODULE + '.Context.current')
    def test_call(self, context, monitor):
        method = Mock(return_value=18)
        pipe = Pipe()
        pipe.reader.close = Mock()
        call = Call(method, 1, 2, a=1, b=2)

        # test
        call(pipe)

        # validation
        pipe.reader.close.assert_called_once_with()
        monitor.assert_called_once_with(pipe.writer)
        monitor.return_value.start.assert_called_once_with()
        reply = protocol.Reply.read(pipe.reader)
        self.assertTrue(isinstance(context.return_value.progress, Progress))
        self.assertEqual(reply.code, protocol.Result.CODE)
        self.assertEqual(reply.payload, method.return_value)

    @patch(MODULE + '.ParentMonitor', Mock())
    @patch(MODULE + '.Context.current', Mock())
    def test_call_pipe_broken(self):
        def method():
            pass
        pipe = Pipe()
        call = Call(method)
        call(pipe)

    @patch(MODULE + '.ParentMonitor', Mock())
    def test_call_exception(self):
        method = Mock(side_effect=ValueError)
        pipe = Pipe()
        pipe.reader.close = Mock()
        call = Call(method)

        # test
        call(pipe)
        reply = protocol.Reply.read(pipe.reader)

        # validation
        self.assertEqual(reply.code, protocol.Raised.CODE)


class TestParentMonitor(TestCase):

    @patch('sys.exit')
    @patch(MODULE + '.Thread.aborted')
    @patch(MODULE + '.sleep', Mock())
    def test_run(self, aborted, _exit):
        def fake_exit(n):
            aborted.return_value = True
        aborted.return_value = False
        pipe = Mock()
        _exit.side_effect = fake_exit
        pipe.put.side_effect = PipeBroken

        # test
        monitor = ParentMonitor(pipe)
        monitor.run()

        # validation
        _exit.assert_called_once_with(1)
