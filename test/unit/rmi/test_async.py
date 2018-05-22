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

from six import unichr

from unittest import TestCase
from mock import Mock

from gofer.compat import str
from gofer.messaging import Document
from gofer.rmi.async import (
    AsyncReply,
    FinalReply,
    Failed,
    Succeeded,
    Accepted,
    Rejected,
    Started,
    Progress,
)

document = Document(
    sn='123',
    routing=['A', 'B'],
    timestamp='XX',
    data={'msg': 'Hello' + unichr(255)},
    result={
        'xmodule': ValueError.__module__,
        'xclass': ValueError.__name__,
        'xargs': 'Failed' + unichr(255),
        'xstate': {},
    },
    total=100,
    completed=10,
    details='Done' + unichr(255))


class Listener(object):
    def __init__(self):
        self.accepted = Mock()
        self.rejected = Mock()
        self.started = Mock()
        self.progress = Mock()
        self.succeeded = Mock()
        self.failed = Mock()


class TestAsyncReply(TestCase):

    def test_init(self):
        reply = AsyncReply(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)

    def test_str(self):
        reply = AsyncReply(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestAccepted(TestCase):

    def test_init(self):
        reply = Accepted(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)

    def test_notify(self):
        l = Listener()
        reply = Accepted(document)
        reply.notify(l)
        l.accepted.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_str(self):
        reply = Accepted(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestRejected(TestCase):

    def test_init(self):
        reply = Rejected(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)

    def test_notify(self):
        l = Listener()
        reply = Rejected(document)
        reply.notify(l)
        l.rejected.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_str(self):
        reply = Rejected(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestStarted(TestCase):

    def test_init(self):
        reply = Started(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)

    def test_notify(self):
        l = Listener()
        reply = Started(document)
        reply.notify(l)
        l.started.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_str(self):
        reply = Started(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestProgress(TestCase):

    def test_init(self):
        reply = Progress(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)
        self.assertEqual(reply.total, document.total)
        self.assertEqual(reply.completed, document.completed)
        self.assertEqual(reply.details, document.details)

    def test_notify(self):
        l = Listener()
        reply = Progress(document)
        reply.notify(l)
        l.progress.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_str(self):
        reply = Progress(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestFinalReply(TestCase):

    def test_notify(self):
        l = Listener()
        reply = FinalReply(document)
        reply.notify(l)
        l.failed.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)


class TestSucceeded(TestCase):

    def test_init(self):
        reply = Succeeded(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)
        self.assertFalse(reply.failed())
        self.assertTrue(reply.succeeded())

    def test_notify(self):
        l = Listener()
        reply = Succeeded(document)
        reply.notify(l)
        l.succeeded.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_str(self):
        reply = Succeeded(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))


class TestFailed(TestCase):

    def test_init(self):
        reply = Failed(document)
        self.assertEqual(reply.sn, document.sn)
        self.assertEqual(reply.origin, document.routing[0])
        self.assertEqual(reply.timestamp, document.timestamp)
        self.assertEqual(reply.data, document.data)
        self.assertTrue(reply.failed())
        self.assertFalse(reply.succeeded())

    def test_notify(self):
        l = Listener()
        reply = Failed(document)
        reply.notify(l)
        l.failed.assert_called_once_with(reply)
        f = Mock()
        reply.notify(f)
        f.assert_called_once_with(reply)

    def test_throw(self):
        reply = Failed(document)
        try:
            reply.throw()
        except ValueError:
            pass

    def test_str(self):
        reply = Failed(document)
        s = str(reply)
        self.assertTrue(isinstance(s, str))
