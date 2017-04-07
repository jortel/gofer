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

from mock import Mock

from gofer.rmi.model.protocol import End
from gofer.rmi.model.protocol import Message, Call, Reply
from gofer.rmi.model.protocol import Progress, Result, Error, Raised, Ping


class Pipe(object):

    def __init__(self):
        self.pipe = []
        self.poll = Mock()

    def put(self, thing):
        self.pipe.append(thing)

    def get(self):
        return self.pipe.pop()


class Person(Message):

    def __init__(self):
        self.name = None
        self.age = None


class TestEnd(TestCase):

    def test_init(self):
        end = End(18)
        self.assertEqual(end.result, 18)


class TestMessage(TestCase):

    def test_send_read(self):
        p_in = Person()
        p_in.name = 'john'
        p_in.age = 18
        pipe = Pipe()

        # test
        p_in.send(pipe)
        p = Person.read(pipe)

        # validation
        pipe.poll.assert_called_once_with()
        self.assertTrue(isinstance(p, Person))
        self.assertEqual(p.name, p_in.name)
        self.assertEqual(p.age, p_in.age)

    def test_read_end(self):
        pipe = Pipe()
        pipe.put(0)
        self.assertRaises(End, Person.read, pipe)


class TestRequest(TestCase):

    def test_init(self):
        # test
        method = Mock()
        args = (1, 2)
        kwargs = dict(a=1, b=2)
        call = Call(method, *args, **kwargs)

        # validation
        self.assertEqual(call.method, method)
        self.assertEqual(call.args, args)
        self.assertEqual(call.kwargs, kwargs)


class TestReply(TestCase):

    def test_register(self):
        code = 18
        target = Mock()
        Reply.register(code, target)
        self.assertEqual(Reply.registry[code], target)

    def test_call(self):
        code = 18
        payload = 1234
        target = Mock()
        Reply.register(code, target)

        # test
        reply = Reply(code, payload)
        reply()

        # validation
        target.assert_called_once_with(payload)
        target.return_value.assert_called_once_with()

    def test_call_not_found(self):
        reply = Reply(44, '')
        reply()


class TestReplies(TestCase):

    def test_progress(self):
        payload = Mock()
        reply = Progress(payload)
        self.assertEqual(reply.code, Progress.CODE)
        self.assertEqual(reply.payload, payload)

    def test_error(self):
        payload = Mock()
        reply = Error(payload)
        self.assertEqual(reply.code, Error.CODE)
        self.assertEqual(reply.payload, payload)

    def test_result(self):
        payload = Mock()
        reply = Result(payload)
        self.assertEqual(reply.code, Result.CODE)
        self.assertEqual(reply.payload, payload)

    def test_raised(self):
        payload = Mock()
        reply = Raised(payload)
        self.assertEqual(reply.code, Raised.CODE)
        self.assertEqual(reply.payload, payload)

    def test_ping(self):
        payload = Mock()
        reply = Ping(payload)
        self.assertEqual(reply.code, Ping.CODE)
        self.assertEqual(reply.payload, payload)
