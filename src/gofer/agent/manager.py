#
# Copyright (c) 2015 Red Hat, Inc.
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

import struct

from logging import getLogger
from socket import socket as Socket
from socket import AF_INET, SOCK_STREAM, IPPROTO_TCP
from socket import TCP_NODELAY, SOL_SOCKET, SO_REUSEADDR, SO_LINGER

from gofer.common import Thread
from gofer.messaging import Document
from gofer.agent.plugin import Container


HOST = 'localhost'
PORT = 5650


log = getLogger(__name__)


class Handler(object):
    """
    The request handler.
    """

    def show(self):
        builtin, _ = Container.builtins()
        admin = builtin.Admin()
        return admin.help()

    def load(self, path):
        container = Container()
        return container.load(path)

    def reload(self, path):
        container = Container()
        return container.reload(path)

    def unload(self, path):
        container = Container()
        return container.unload(path)


class Manager(Thread):
    """
    The manager thread.
    """

    def __init__(self, host=None, port=None, handler=None):
        """
        :param host: The host (interface) to listen on.
        :type: host: str
        :param port: The port to listen on.
        :type: port: int
        :param handler: The request handler.
        :type handler: Handler
        """
        super(Manager, self).__init__(name='manager')
        self.host = host or HOST
        self.port = port or port
        self.handler = handler or Handler()
        self.setDaemon(True)

    def listen(self):
        """
        Bind and listen.
        :return: The open socket.
        :rtype: socket.socket
        """
        address = (self.host, self.port)
        socket = Socket(AF_INET, SOCK_STREAM)
        socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        socket.bind(address)
        socket.listen(5)
        log.info('listening on: %d', self.port)
        return socket

    def accept(self, socket):
        """
        Accept requests.
        :param socket: An open socket.
        :type socket: socket.socket
        """
        while not Thread.aborted():
            client, address = socket.accept()
            try:
                self.accepted(client)
            finally:
                client.close()

    def accepted(self, client):
        """
        Process the request on the accepted socket.
        :param client: A client socket.
        :type client: socket.socket
        """
        try:
            client.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
            client.setsockopt(SOL_SOCKET, SO_LINGER, struct.pack('ii', 1, 1))
            message = client.recv(4096)
            call = Document()
            call.load(message)
            reply = self.dispatch(call)
            client.send(reply)
        except Exception, e:
            log.error(str(e))

    def run(self):
        """
        The thread main.
        """
        try:
            socket = self.listen()
            self.accept(socket)
        except Exception:
            log.exception(self.host)

    def dispatch(self, call):
        """
        Dispatch the call to the handler.
        :param call: A *call* document.
        :type call: Document
        """
        reply = Document()
        try:
            method = getattr(self.handler, call.name)
            result = method(*call.args, **call.kwargs)
            reply.code = 0
            reply.result = result
        except Exception, e:
            reply.code = 1
            reply.result = str(e)
        return reply.dump()


class Method(object):
    """
    Remote method.
    """

    def __init__(self, host, port, name):
        """
        :param host: The host used to connect to the manager.
        :type host: str
        :param port: The port used to connect to the manager.
        :type: port: int
        :param name: The method name.
        :type name: str
        """
        self.name = name
        self.address = (host, port)

    def call(self, *args, **kwargs):
        """
        Remote call.
        """
        socket = Socket(AF_INET, SOCK_STREAM)
        socket.connect(self.address)
        try:
            method = Document()
            method.name = self.name
            method.args = args
            method.kwargs = kwargs
            socket.send(method.dump())
            reply = socket.recv(4096)
            result = Document()
            result.load(reply)
            return result
        finally:
            socket.close()

    def __call__(self, *args, **kwargs):
        try:
            result = self.call(*args, **kwargs)
        except Exception, e:
            reply = Document()
            reply.code = 1
            reply.result = str(e)
            result = reply
        return result


class Client(object):
    """
    The remote manager client.
    """

    def __init__(self, host=None, port=None):
        """
        :param port: The port used to connect to the manager.
        :type: port: int
        """
        self.host = host or HOST
        self.port = port or PORT

    def __getattr__(self, name):
        return Method(self.host, self.port, name)
