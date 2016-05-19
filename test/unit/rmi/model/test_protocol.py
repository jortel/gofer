from unittest import TestCase

from mock import Mock

from gofer.rmi.model.protocol import End
from gofer.rmi.model.protocol import Message, Call, Reply
from gofer.rmi.model.protocol import Progress, Result, Error, Raised


class Pipe(object):

    def __init__(self):
        self.pipe = []

    def send(self, thing):
        self.pipe.append(thing)

    def recv(self):
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
        self.assertTrue(isinstance(p, Person))
        self.assertEqual(p.name, p_in.name)
        self.assertEqual(p.age, p_in.age)

    def test_read_end(self):
        pipe = Pipe()
        pipe.send(0)
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
