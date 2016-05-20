from unittest import TestCase

from mock import patch, Mock

from gofer.rmi.model.child import Progress, Call
from gofer.rmi.model import protocol


MODULE = 'gofer.rmi.model.child'


class Pipe(object):

    def __init__(self):
        self.pipe = []

    def send(self, thing):
        self.pipe.append(thing)

    def recv(self):
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
