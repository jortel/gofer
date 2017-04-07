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

from mock import Mock, patch

from gofer.mp import Process, Pipe, Endpoint, Reader, Writer, PipeBroken
from gofer.mp import EPOLLIN, EPOLLHUP


MODULE = 'gofer.mp'


class Thing(object):

    def __eq__(self, other):
        return isinstance(other, Thing) and self.__dict__ == other.__dict__


class TestProcess(TestCase):

    def test_init(self):
        main = Mock()
        args = (1, 2)
        kwargs = {'a': 3, 'b': 4}

        # test
        p = Process(main, *args, **kwargs)

        # validation
        self.assertEqual(p.main, main)
        self.assertEqual(p.args, (1, 2))
        self.assertEqual(p.kwargs, {'a': 3, 'b': 4})

    @patch('os.fork')
    @patch(MODULE + '.Process.run')
    def test_start_child(self, run, fork):
        fork.return_value = 0
        p = Process(Mock())

        # test
        p.start()

        # validation
        fork.assert_called_once_with()
        run.assert_called_once_with()

    @patch('os.fork')
    @patch(MODULE + '.Process.run')
    def test_start_parent(self, run, fork):
        fork.return_value = 1234
        p = Process(Mock())

        # test
        p.start()

        # validation
        fork.assert_called_once_with()
        self.assertFalse(run.called)
        self.assertEqual(p.pid, fork.return_value)

    def test_run(self):
        main = Mock()
        args = (1, 2)
        kwargs = {'a': 3, 'b': 4}

        # test
        p = Process(main, *args, **kwargs)
        p.run()

        # validation
        p.main.assert_called_once_with(*args, **kwargs)

    @patch('os.kill')
    def test_terminate(self, kill):
        p = Process(Mock())
        p.pid = 1234
        p.terminate()
        kill.assert_called_once_with(p.pid, 9)

    @patch('os.kill')
    def test_terminate_not_forked(self, kill):
        p = Process(Mock())
        p.terminate()
        self.assertFalse(kill.called)

    @patch('os.waitpid')
    def test_wait(self, wait):
        p = Process(Mock())
        p.wait()
        wait.assert_called_once_with(p.pid, 0)

    @patch('os.waitpid')
    def test_wait_error(self, wait):
        wait.side_effect = OSError()
        p = Process(Mock())
        p.wait()
        wait.assert_called_once_with(p.pid, 0)


class TestPipe(TestCase):

    @patch('os.pipe')
    def test_open(self, pipe):
        pipe.return_value = 0, 1
        reader, writer = Pipe._open()
        self.assertEqual(reader.fd, 0)
        self.assertEqual(writer.fd, 1)

    @patch(MODULE + '.Pipe._open')
    def test_init(self, _open):
        _open.return_value = Reader(0), Writer(1)
        p = Pipe()
        self.assertTrue(isinstance(p.reader, Reader))
        self.assertTrue(isinstance(p.writer, Writer))
        self.assertEqual(p.reader.fd, 0)
        self.assertEqual(p.writer.fd, 1)

    @patch(MODULE + '.Pipe._open')
    def test_close(self, _open):
        _open.return_value = Mock(), Mock()
        p = Pipe()
        p.close()
        _open.return_value[0].close.assert_called_once_with()
        _open.return_value[1].close.assert_called_once_with()

    @patch(MODULE + '.Pipe._open')
    def test_poll(self, _open):
        _open.return_value = Mock(), Mock()
        p = Pipe()
        p.poll()
        _open.return_value[0].poll.assert_called_once_with()

    @patch(MODULE + '.Pipe._open')
    def test_get(self, _open):
        _open.return_value = Mock(), Mock()
        p = Pipe()
        thing = p.get()
        _open.return_value[0].get.assert_called_once_with()
        self.assertEqual(thing, _open.return_value[0].get.return_value)

    @patch(MODULE + '.Pipe._open')
    def test_put(self, _open):
        _open.return_value = Mock(), Mock()
        thing = Thing()
        p = Pipe()
        p.put(thing)
        _open.return_value[1].put.assert_called_once_with(thing)

    @patch(MODULE + '.Pipe._open')
    def test_enter(self, _open):
        _open.return_value = Mock(), Mock()
        p = Pipe()
        self.assertEqual(p.__enter__(), p)

    @patch(MODULE + '.Pipe.close')
    @patch(MODULE + '.Pipe._open')
    def test_exit(self, _open, close):
        _open.return_value = Mock(), Mock()
        p = Pipe()
        p.__exit__()
        close.assert_called_once_with()


class TestEndpoint(TestCase):

    def test_init(self):
        fd = 18
        endpoint = Endpoint(fd)
        self.assertEqual(endpoint.fd, fd)

    @patch('os.close')
    def test_close(self, close):
        endpoint = Endpoint(18)
        endpoint.close()
        close.assert_called_once_with(endpoint.fd)


class TestReader(TestCase):

    @patch(MODULE + '.epoll')
    def test_init(self, epoll):
        fd = 18
        reader = Reader(fd)
        self.assertEqual(reader.fd, fd)
        self.assertEqual(reader.epoll, epoll.return_value)
        epoll.return_value.register.assert_called_once_with(reader.fd, EPOLLIN | EPOLLHUP)

    def test_write_read(self):
        thing = Thing()
        p = Pipe()
        p.put(thing)
        read = p.reader.get()
        p.close()
        self.assertEqual(read, thing)

    def test_multiple_write_read(self):
        things = [
            Thing(),
            Thing(),
            Thing()
        ]
        p = Pipe()
        for t in things:
            p.put(t)
        read = []
        for _ in things:
            read.append(p.reader.get())
        p.close()
        self.assertEqual(read, things)

    def test_eof(self):
        p = Pipe()
        p.writer.close()
        self.assertRaises(EOFError, p.reader.get)
        p.close()

    @patch(MODULE + '.epoll')
    def test_poll(self, epoll):
        fd = 1234
        r = Reader(fd)
        r.poll()
        epoll.return_value.poll.assert_called_once_with()


class TestWriter(TestCase):

    @patch('os.write')
    def test_pipe_broken(self, write):
        write.side_effect = PipeBroken
        writer = Writer(0)
        self.assertRaises(PipeBroken, writer.put, '')
