from StringIO import StringIO
from unittest import TestCase

from mock import Mock

from gofer.common import json
from gofer.rmi.mode.protocol import End, ProtocolError
from gofer.rmi.mode.protocol import Message, Request, Reply
from gofer.rmi.mode.protocol import Progress, Result, Error, Raised


class Person(Message):

    def __init__(self):
        self.name = None
        self.age = None


class TestExceptions(TestCase):

    def test_end(self):
        end = End(18)
        self.assertEqual(end.result, 18)

    def test_protocol_error(self):
        ProtocolError()


class TestMessage(TestCase):

    def test_load(self):
        p_in = Person()
        p_in.name = 'john'
        p_in.age = 18
        message = json.dumps(p_in.__dict__)

        # test
        p = Person.load(message)

        # validation
        self.assertTrue(isinstance(p, Person))
        self.assertEqual(p.name, p_in.name)
        self.assertEqual(p.age, p_in.age)

    def test_send_read(self):
        p_in = Person()
        p_in.name = 'john'
        p_in.age = 18
        pipe = StringIO()

        # test
        pipe.write('trash\n')
        p_in.send(pipe)
        pipe.seek(0)
        p = Person.read(pipe)

        # validation
        self.assertTrue(isinstance(p, Person))
        self.assertEqual(p.name, p_in.name)
        self.assertEqual(p.age, p_in.age)

    def test_read_end(self):
        pipe = StringIO()
        self.assertRaises(End, Person.read, pipe)


class TestRequest(TestCase):

    def test_init(self):
        path = '/tmp/x'
        mod = 'test'
        target = 'Dog'
        state = {'A': 1}
        method = 'bark'
        passed = ([18], {'B': 2})

        # test
        r = Request(
            path=path,
            mod=mod,
            target=target,
            state=state,
            method=method,
            passed=passed)

        # validation
        self.assertEqual(r.path, path)
        self.assertEqual(r.mod, r.mod)
        self.assertEqual(r.target, target)
        self.assertEqual(r.state, state)
        self.assertEqual(r.method, method)
        self.assertEqual(r.passed, passed)


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
