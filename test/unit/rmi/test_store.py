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

from unittest import TestCase
from mock import Mock

from gofer.rmi.store import Pending, Sequential

from gofer.devel import patch


class TestPendingQueue(TestCase):

    @patch('__builtin__.open')
    def test_write(self, _open):
        def _enter():
            return _open.return_value

        def _exit(*unused):
            _open.return_value.close()

        _open.return_value.__enter__ = Mock(side_effect=_enter)
        _open.return_value.__exit__ = Mock(side_effect=_exit)
        request = Mock()
        path = '/tmp/123'
        Pending._write(request, path)
        _open.assert_called_once_with(path, 'w+')
        _open.return_value.write.assert_called_once_with(request.dump.return_value)
        _open.return_value.close.assert_called_once_with()

    @patch('__builtin__.open')
    @patch('gofer.rmi.store.unlink')
    def test_read(self, unlink, _open):
        def _enter():
            return _open.return_value

        def _exit(*unused):
            _open.return_value.close()

        _open.return_value.__enter__ = Mock(side_effect=_enter)
        _open.return_value.__exit__ = Mock(side_effect=_exit)
        body = '{"A": 1}'
        _open.return_value.read.return_value = body
        path = '/tmp/123'
        document = Pending._read(path)
        _open.assert_called_once_with(path)
        _open.return_value.read.assert_called_once_with()
        _open.return_value.close.assert_called_once_with()
        self.assertFalse(unlink.called)
        self.assertEqual(document.__dict__, {'A': 1})

    @patch('__builtin__.open')
    @patch('gofer.rmi.store.unlink')
    def test_read_invalid_json(self, unlink, _open):
        def _enter():
            return _open.return_value

        def _exit(*unused):
            _open.return_value.close()

        _open.return_value.__enter__ = Mock(side_effect=_enter)
        _open.return_value.__exit__ = Mock(side_effect=_exit)
        body = '__invalid__'
        _open.return_value.read.return_value = body
        path = '/tmp/123'
        document = Pending._read(path)
        _open.assert_called_once_with(path)
        _open.return_value.read.assert_called_once_with()
        _open.return_value.close.assert_called_once_with()
        unlink.assert_called_once_with(path)
        self.assertEqual(document, None)

    @patch('gofer.rmi.store.unlink')
    @patch('gofer.rmi.store.Thread', Mock())
    def test_commit(self, unlink):
        sn = '123'
        path = '/tmp/123'
        p = Pending('')
        p.journal = {sn: path}
        p.commit(sn)
        unlink.assert_called_once_with(path)
        self.assertEqual(p.journal, {})

    @patch('gofer.rmi.store.unlink')
    @patch('gofer.rmi.store.Thread', Mock())
    def test_commit_not_found(self, unlink):
        sn = '123'
        path = '/tmp/123'
        p = Pending('')
        p.journal = {sn: path}
        p.commit('invalid')
        self.assertFalse(unlink.called)
        self.assertEqual(p.journal, {sn: path})


class TestSequential(TestCase):

    def test_init(self):

        s = Sequential()
        self.assertEqual(s.n, 0)
        self.assertEqual(s.last, 0.0)

    @patch('gofer.rmi.store.time')
    def test_next_time_stopped(self, time):
        time.return_value = 3.14
        s = Sequential()
        values = [
            s.next(),
            s.next(),
            s.next(),
        ]
        self.assertEqual(
                values,
                [
                    '3-140000-0000.json',
                    '3-140000-0001.json',
                    '3-140000-0002.json'
                ])

    @patch('gofer.rmi.store.time')
    def test_next_time_moving(self, time):
        time.side_effect = [3.14, 3.15, 3.16]
        s = Sequential()
        values = [
            s.next(),
            s.next(),
            s.next(),
        ]
        self.assertEqual(
                values,
                [
                    '3-140000-0000.json',
                    '3-150000-0000.json',
                    '3-160000-0000.json'
                ])
