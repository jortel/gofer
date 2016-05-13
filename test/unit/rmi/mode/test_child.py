from StringIO import StringIO
from unittest import TestCase

from mock import patch

from gofer.agent.rmi import Context, Cancelled
from gofer.rmi.mode.child import TargetNotFound, MethodNotFound
from gofer.rmi.mode.child import Progress, Raised, Request, main
from gofer.rmi.mode import protocol


MODULE = 'gofer.rmi.mode.child'


class Dog(object):
    def __init__(self):
        self.name = 'Rover'

    def bark(self, w, b):
        return w.upper(), b.upper()

    def failed(self):
        raise ValueError('This failed')


class Cat:
    def __init__(self):
        self.name = 'Morris'

    def meow(self):
        pass


def function():
    pass


class Mod(object):
    Dog = Dog
    Cat = Cat
    function = function


class TestExceptions(TestCase):

    def test_target_not_found(self):
        name = 'test'
        raised = Exception()
        exception = TargetNotFound(name, raised)
        self.assertEqual(exception.args, (TargetNotFound.FORMAT % (name, str(raised)),))

    def test_method_not_found(self):
        name = 'test'
        exception = MethodNotFound(name)
        self.assertEqual(exception.args, (MethodNotFound.FORMAT % name,))


class TestProgress(TestCase):

    def test_report(self):
        p = Progress()
        p.total = 1
        p.completed = 2
        p.details = 'hello'
        stdout = StringIO()

        # test
        with patch(MODULE + '.stdout', stdout):
            p.report()

        # validation
        stdout.seek(0)
        reply = protocol.Reply.read(stdout)
        payload = protocol.Progress.Payload(**reply.payload)
        self.assertEqual(reply.code, protocol.Progress.CODE)
        self.assertEqual(payload.total, p.total)
        self.assertEqual(payload.completed, p.completed)
        self.assertEqual(payload.details, p.details)


class TestRaised(TestCase):

    def test_current(self):
        message = 'This is bad'
        exception = ValueError(message)
        try:
            raise exception
        except ValueError:
            pass

        # test
        payload = Raised.current()

        # validation
        state = exception.__dict__
        state['trace'] = payload.description
        self.assertEqual(payload.args, (message,))
        self.assertTrue(payload.description.startswith('Trace'))
        self.assertEqual(payload.mod, ValueError.__module__)
        self.assertEqual(payload.state, state)
        self.assertEqual(payload.target, exception.__class__.__name__)

    @patch(MODULE + '.Raised.current')
    def test_init(self, current):
        current.return_value.__dict__ = {'A': 1}

        # test
        r = Raised()

        # validation
        self.assertEqual(r.payload, current.return_value.__dict__)


class TestRequest(TestCase):

    def test_get_module(self):
        request = Request(
            path='/tmp/file.py',
            mod='test.mod',
            target='Dog',
            state={},
            method='bark',
            passed=([], {}))

        # test
        with patch('__builtin__.__import__') as _import:
            mod = request.get_module()

        # validation
        _import.assert_called_once_with(request.mod, fromlist=[request.target])
        self.assertEqual(mod, _import.return_value)

    def test_get_module_from_file(self):
        request = Request(
            path='/tmp/file.py',
            mod='test',
            target='Dog',
            state={},
            method='bark',
            passed=([], {}))

        # test
        with patch(MODULE + '.imp.load_source') as load:
            mod = request.get_module()

        # validation
        load.assert_called_once_with(request.mod, request.path)
        self.assertEqual(mod, load.return_value)

    def test_get_target_object(self):
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=Dog().__class__.__name__,
            state=Dog().__dict__,
            method='bark',
            passed=([], {}))

        # test
        with patch(MODULE + '.Request.get_module') as get_mod:
            get_mod.return_value = Mod
            target = request.get_target()

        # validation
        self.assertTrue(isinstance(target, Dog))
        self.assertEqual(target.name, Dog().name)

    def test_get_target_not_object(self):
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=Cat().__class__.__name__,
            state=Cat().__dict__,
            method='meow',
            passed=([], {}))

        # test
        with patch(MODULE + '.Request.get_module') as get_mod:
            get_mod.return_value = Mod
            target = request.get_target()

        # validation
        self.assertTrue(isinstance(target, Cat))
        self.assertEqual(target.name, Cat().name)

    def test_get_target_function(self):
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=function.__name__,
            state={},
            method='',
            passed=([], {}))

        # test
        with patch(MODULE + '.Request.get_module') as get_mod:
            get_mod.return_value = Mod
            target = request.get_target()

        # validation
        self.assertEqual(target, Mod)

    def test_get_target_not_found(self):
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target='123',
            state={},
            method='',
            passed=([], {}))

        # test
        with patch(MODULE + '.Request.get_module') as get_mod:
            get_mod.return_value = Mod
            self.assertRaises(TargetNotFound, request.get_target)

    def test_get_method(self):
        inst = Dog()
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=inst.__class__.__name__,
            state=inst.__dict__,
            method=inst.bark.__name__,
            passed=([], {}))

        # test
        method = request.get_method(inst)

        # validation
        self.assertEqual(method, inst.bark)

    def test_get_method_not_found(self):
        inst = Dog()
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=inst.__class__.__name__,
            state=inst.__dict__,
            method='123',
            passed=([], {}))

        # test
        self.assertRaises(MethodNotFound, request.get_method, inst)

    def test_call(self):
        inst = Dog()
        a = 'hello'
        b = 'world'
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=inst.__class__.__name__,
            state=inst.__dict__,
            method=inst.bark.__name__,
            passed=([a], {'b': b}))

        stdout = StringIO()

        # test
        with patch(MODULE + '.stdout', stdout):
            request()
        stdout.seek(0)
        reply = protocol.Reply.read(stdout)
        self.assertEqual(reply.code, protocol.Result.CODE)
        self.assertEqual(reply.payload, list(inst.bark(a, b)))

    def test_call_raised(self):
        inst = Dog()
        a = 'hello'
        b = 'world'
        request = Request(
            path='/tmp/file.py',
            mod=__name__,
            target=inst.__class__.__name__,
            state=inst.__dict__,
            method=inst.failed.__name__,
            passed=([a], {'b': b}))

        stdout = StringIO()

        # test
        with patch(MODULE + '.stdout', stdout):
            request()
        stdout.seek(0)
        reply = protocol.Reply.read(stdout)
        self.assertEqual(reply.code, protocol.Raised.CODE)


class TestMain(TestCase):

    @patch(MODULE + '.stdin')
    @patch(MODULE + '.Request.read')
    @patch(MODULE + '.LogHandler.install')
    def test_main(self, install, read, stdin):
        # test
        main()

        # validation
        install.assert_called_once_with()
        read.assert_called_once_with(stdin)
        context = Context.current()
        self.assertTrue(isinstance(context.progress, Progress))
        self.assertTrue(isinstance(context.cancelled, Cancelled))
        self.assertEqual(context.cancelled.sn, '')
