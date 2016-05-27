from unittest import TestCase

from mock import Mock, patch

from gofer.rmi.context import Context, Progress, Cancelled


MODULE = 'gofer.rmi.context'


class TestContext(TestCase):

    def setUp(self):
        Context._current.inst = None

    def tearDown(self):
        Context._current.inst = None

    def test_init(self):
        sn = '1'
        progress = Mock()
        cancelled = Mock()
        context = Context(sn, progress, cancelled)
        self.assertEqual(context.sn, sn)
        self.assertEqual(context.progress, progress)
        self.assertEqual(context.cancelled, cancelled)

    def test_set(self):
        context = Context('1', Mock(), Mock())
        Context.set(context)
        # set
        self.assertEqual(Context._current.inst, context)
        # clear
        Context.set()
        self.assertEqual(Context._current.inst, None)


class TestProgress(TestCase):

    def test_report(self):
        request = Mock(sn=1, data=2, replyto=3)
        producer = Mock()
        progress = Progress(request, producer)
        progress.total = 10
        progress.completed = 4
        progress.details = {'A': 1}

        # test
        progress.report()

        # validation
        producer.send.assert_called_once_with(
            request.replyto,
            status='progress',
            completed=progress.completed,
            details=progress.details,
            total=progress.total,
            data=request.data,
            sn=1)

    @patch(MODULE + '.log')
    def test_report_exception(self, log):
        request = Mock(sn=1, data=2, replyto=3)
        producer = Mock()
        producer.send.side_effect = ValueError()
        progress = Progress(request, producer)

        # test
        progress.report()

        # validation
        self.assertTrue(log.exception.called)

    def test_report_no_replyto(self):
        request = Mock(sn=1, data=2, replyto=None)
        producer = Mock()
        progress = Progress(request, producer)

        # test
        progress.report()

        # validation
        self.assertFalse(producer.send.called)


class TestCancelled(TestCase):

    @patch(MODULE + '.Tracker')
    def test_call(self, tracker):
        sn = '1'
        cancelled = Cancelled(sn)
        r = cancelled()
        tracker.assert_called_once_with()
        tracker.return_value.cancelled.assert_called_once_with(sn)
        self.assertEqual(r, tracker.return_value.cancelled.return_value)

    @patch(MODULE + '.Tracker')
    def test_del(self, tracker):
        sn = '1'
        cancelled = Cancelled(sn)
        cancelled.__del__()
        tracker.return_value.remove.assert_called_once_with(sn)

    @patch(MODULE + '.Tracker')
    def test_del_key_error(self, tracker):
        sn = '1'
        tracker.return_value.remove.side_effect = KeyError()
        cancelled = Cancelled(sn)
        cancelled.__del__()
