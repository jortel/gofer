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

from gofer.rmi.model.child import Progress, Call
from gofer.rmi.model import protocol


MODULE = 'gofer.rmi.model.child'


class Pipe(object):

    def __init__(self):
        self.pipe = []
        self.poll = Mock()

    def put(self, thing):
        self.pipe.append(thing)

    def get(self):
        return self.pipe.pop()


class TestProgress(TestCase):

    def test_report(self):
        pipe = Pipe()
        p = Progress(pipe)
        p.total = 1
        p.completed = 2
        p.details = 'hello'

        # test
        p.report()

        # validation
        reply = protocol.Reply.read(pipe)
        self.assertEqual(reply.code, protocol.Progress.CODE)
        self.assertEqual(reply.payload.total, p.total)
        self.assertEqual(reply.payload.completed, p.completed)
        self.assertEqual(reply.payload.details, p.details)


class TestCall(TestCase):

    @patch(MODULE + '.Context.current')
    def test_call(self, context):
        method = Mock(return_value=18)
        pipe = Pipe()
        call = Call(method, 1, 2, a=1, b=2)

        # test
        call(pipe)

        # validation
        reply = protocol.Reply.read(pipe)
        self.assertTrue(isinstance(context.return_value.progress, Progress))
        self.assertEqual(reply.code, protocol.Result.CODE)
        self.assertEqual(reply.payload, method.return_value)

    def test_call_exception(self):
        method = Mock(side_effect=ValueError)
        pipe = Pipe()
        call = Call(method, 1, 2, a=1, b=2)

        # test
        call(pipe)
        reply = protocol.Reply.read(pipe)

        # validation
        self.assertEqual(reply.code, protocol.Raised.CODE)
