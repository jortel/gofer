from unittest import TestCase
from logging import LogRecord
from subprocess import PIPE

from mock import call, patch, Mock

from gofer.rmi.mode import protocol
from gofer.rmi.mode.parent import Monitor, Result, Progress, Error, Raised, Request
from gofer.rmi.mode.parent import python
from gofer.rmi.mode import child


MODULE = 'gofer.rmi.mode.parent'


class Dog(object):

    def __init__(self):
        self.name = 'Maddie'
        self.age = 4

    def bark(self):
        pass


class TestMonitor(TestCase):

    @patch(MODULE + '.sleep')
    def test_run(self, sleep):
        context = Mock()
        context.cancelled.side_effect = [False, True]
        child = Mock()

        # test
        m = Monitor(context, child)
        m.run()

        # validation
        child.terminate.assert_called_once_with()
        sleep.assert_called_once_with(0.10)

    @patch(MODULE + '.Monitor.join')
    def test_stop(self, join):
        context = Mock()
        child = Mock()

        # test
        m = Monitor(context, child)
        m.stop()

        # validation
        self.assertEqual(m.poll, False)
        join.assert_called_once_with()


class TestReplies(TestCase):

    def test_result(self):
        payload = 'done'
        reply = Result(payload)

        # test
        try:
            reply()
            self.fail(msg='End not raised')
        except protocol.End, end:
            self.assertEqual(end.result, payload)

    @patch(MODULE + '.Context.current')
    def test_progress(self, current):
        class P(object):
            report = Mock()
        context = Mock()
        context.progress = P()
        current.return_value = context
        payload = protocol.Progress.Payload(1, 2, 3)
        reply = Progress(payload.__dict__)

        # test
        reply()

        context.progress.report.assert_called_once_with()
        self.assertEqual(context.progress.__dict__, payload.__dict__)

    def test_error(self):
        payload = 18
        reply = Error(payload)
        self.assertRaises(Exception, reply)

    def test_raised(self):
        payload = Raised.Payload(
            description='This Failed',
            mod='exceptions',
            target='ValueError',
            state={'A': 1},
            args=[1, 2])

        # test
        reply = Raised(payload.__dict__)
        try:
            reply()
            self.fail(msg='ValueError not raised')
        except ValueError, e:
            self.assertTrue(isinstance(e, ValueError))

    def test_raised_not_found(self):
        payload = Raised.Payload(
            description='This Failed',
            mod='exceptions',
            target='Test',
            state={'A': 1},
            args=[1, 2])

        # test
        reply = Raised(payload.__dict__)
        try:
            reply()
            self.fail(msg='Exception not raised')
        except Exception, e:
            self.assertTrue(isinstance(e, Exception))
            self.assertEqual(e.args[0], payload.description)

    @patch(MODULE + '.new')
    def test_raised_failed(self, new):
        new.side_effect = RuntimeError()
        payload = Raised.Payload(
            description='This Failed',
            mod='exceptions',
            target='ValueError',
            state={'A': 1},
            args=[1, 2])

        # test
        reply = Raised(payload.__dict__)
        try:
            reply()
            self.fail(msg='Exception not raised')
        except Exception, e:
            self.assertTrue(isinstance(e, Exception))
            self.assertEqual(e.args, tuple(payload.args))


class TestRequest(TestCase):

    def test_build(self):
        dog = Dog()
        passed = ([], {})
        r = Request.build(dog, dog.bark, passed)
        self.assertEqual(r.path, __file__)
        self.assertEqual(r.mod, __name__)
        self.assertEqual(r.target, dog.__class__.__name__)
        self.assertEqual(r.state, dog.__dict__)
        self.assertEqual(r.method, dog.bark.__name__)
        self.assertEqual(r.passed, passed)

    @patch(MODULE + '.Context')
    @patch(MODULE + '.Request.read')
    @patch(MODULE + '.Request.send')
    @patch(MODULE + '.Popen')
    @patch(MODULE + '.Monitor')
    def test_call(self, monitor, p_open, send, read, context):
        p_open.return_value = Mock(stdin=Mock(), stdout=Mock())
        request = Request(
            path='/tmp/file.py',
            mod='test.mod',
            target='Dog',
            state={'A': 1},
            method='bark',
            passed=([1, 2], {'B': 2}))

        # test
        request()

        # validation
        p_open.assert_called_once_with([python, child.__file__], stdin=PIPE, stdout=PIPE)
        monitor.assert_called_once_with(context.current.return_value, p_open.return_value)
        monitor.return_value.start.assert_called_once_with()
        send.assert_called_once_with(p_open.return_value.stdin)
        read.assert_called_once_with(p_open.return_value.stdout)
        monitor.return_value.stop.assert_called_once_with()
        p_open.return_value.stdin.close.assert_called_once_with()
        p_open.return_value.stdout.close.assert_called_once_with()
        p_open.return_value.wait.assert_called_once_with()

    @patch(MODULE + '.protocol.Reply')
    def test_read(self, reply):
        replies = [Mock(), Mock(side_effect=protocol.End(18))]
        reply.read.side_effect = replies
        request = Request(
            path='/tmp/file.py',
            mod='test.mod',
            target='Dog',
            state={'A': 1},
            method='bark',
            passed=([1, 2], {'B': 2}))
        pipe = Mock()

        # test
        retval = request.read(pipe)

        # validation
        self.assertEqual(
            reply.read.call_args_list,
            [
                call(pipe),
                call(pipe)
            ])
        self.assertEqual(retval, 18)
