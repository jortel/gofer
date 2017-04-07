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

import os
import pickle

from errno import EPIPE
from signal import SIGKILL

try:
    from select import epoll, EPOLLIN, EPOLLHUP
except ImportError:
    from select import poll as epoll, POLLIN as EPOLLIN, POLLHUP as EPOLLHUP


class PipeBroken(Exception):
    pass


class Process(object):
    """
    Linux Process.
    :ivar main: The process main.
    :type main: callable
    :ivar args: Argument list.
    :type args: tuple
    :ivar kwargs: Keyword arguments.
    :type kwargs: dict
    :ivar pid: The process ID.
    :type pid: int
    """

    def __init__(self, main, *args, **kwargs):
        self.main = main
        self.args = args
        self.kwargs = kwargs
        self.pid = 0

    def start(self):
        """
        Start the process by forking then calling run().
        """
        pid = os.fork()
        if pid == 0:
            self.pid = os.getpid()
            self.run()
        else:
            self.pid = pid

    def run(self):
        """
        Call main() then terminate the process.
        """
        try:
            self.main(*self.args, **self.kwargs)
        finally:
            self.terminate()

    def terminate(self):
        """
        Terminate the process.
        """
        if self.pid:
            os.kill(self.pid, SIGKILL)

    def wait(self):
        """
        Wait for the process to terminate.
        Swallows raised exceptions.
        """
        try:
            return os.waitpid(self.pid, 0)
        except OSError:
            pass


class Pipe(object):
    """
    Inter-process pipe.
    :ivar reader: The *read* end of the pipe.
    :type reader: Reader
    :ivar writer: The write end of the pipe.
    :ivar writer: Writer
    """

    @staticmethod
    def _open():
        """
        Open (create) the pipe and the *reader* and *writer*.
        :return: A tuple of: (Reader, Writer)
        :rtype: tuple
        """
        read, write = os.pipe()
        return Reader(read), Writer(write)

    def __init__(self):
        """
        Create the pipe.
        """
        self.reader, self.writer = Pipe._open()

    def close(self):
        """
        Close the pipe.
        """
        for endpoint in (self.reader, self.writer):
            endpoint.close()

    def poll(self):
        """
        Poll the *reader*.
        Blocks until data is available to be read or the
        writing end has been closed.
        """
        self.reader.poll()

    def get(self):
        """
        Read the next pickled object from the pipe.
        :return: The next read message.
        :rtype: object
        """
        return self.reader.get()

    def put(self, thing):
        """
        Pickle and write the object into the pipe.
        :param thing: An object.
        :type thing: any
        """
        self.writer.put(thing)

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


class Endpoint(object):
    """
    A Pipe endpoint.
    :ivar fd: An open pipe file descriptor.
    :type fd: int
    """

    # pickled object separator
    EOR = '\x1E'

    def __init__(self, fd):
        """
        :param fd: An open pipe file descriptor.
        :type fd: int
        """
        self.fd = fd

    def close(self):
        """
        Close the associated file descriptor.
        Swallows raised exceptions.
        """
        try:
            os.close(self.fd)
        except:
            pass


class Reader(Endpoint):
    """
    The *reading* end of a Pipe.
    :ivar epoll: A file descriptor polling object.
    :type epoll: socket.poll
    """

    def __init__(self, fd):
        """
        :param fd: An open pipe file descriptor.
        :type fd: int
        """
        super(Reader, self).__init__(fd)
        self.epoll = epoll()
        self.epoll.register(fd, EPOLLIN | EPOLLHUP)

    def get(self):
        """
        Read the next pickled object from the pipe.
        :return: The next read message.
        :rtype: object
        """
        record = []
        while True:
            byte = os.read(self.fd, 1)
            if not byte:
                raise EOFError()
            if byte == Endpoint.EOR:
                break
            record.append(byte)
        if record:
            return pickle.loads(''.join(record))
        else:
            raise EOFError()

    def poll(self):
        """
        Blocks until data is available to be read or the
        writing end has been closed.
        """
        self.epoll.poll()


class Writer(Endpoint):
    """
    The *writing* end of a Pipe.
    """

    def put(self, thing):
        """
        Pickle and write the object into the pipe.
        :param thing: An object.
        :type thing: any
        """
        record = pickle.dumps(thing)
        try:
            os.write(self.fd, record)
            os.write(self.fd, Endpoint.EOR)
        except OSError, pe:
            if pe.errno == EPIPE:
                raise PipeBroken()
            else:
                raise
