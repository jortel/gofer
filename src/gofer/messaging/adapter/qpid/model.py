# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from uuid import uuid4
from logging import getLogger

from qpid.messaging import Message

from gofer.messaging.adapter.model import Messenger, BaseExchange, BaseQueue
from gofer.messaging.adapter.qpid.connection import Connection
from gofer.messaging.adapter.qpid.reliability import reliable


log = getLogger(__name__)


SUBJECT = 'broker'
ADDRESS = 'qmf.default.direct/broker'
REPLY_TO = 'qmf.default.direct/%s;{node:{type:topic},link:{x-declare:{auto-delete:True,exclusive:True}}}'

EEXIST = 7

CREATE = 'create'
DELETE = 'delete'

OBJECT_ID = {
    '_object_name': 'org.apache.qpid.broker:broker:amqp-broker'
}


class Error(Exception):
    """
    General Error.
    :ivar code: The qpid error code.
    :type code: int
    """

    def __init__(self, description, code):
        """
        :param description: Error description.
        :type description: str
        :param code: The qpid error code.
        :type code: int
        """
        Exception.__init__(self, description)
        self.code = code


class Method(Messenger):
    """
    QMF method.
    :ivar name: The method name.
    :type name: str
    :ivar arguments: The method arguments.
    :type arguments: dict
    :ivar connection: A broker connection.
    :type connection: Connection
    :ivar session: An AMQP session.
    :type session: qpid.messaging.Session.
    :ivar sender: A message sender.
    :type sender: qpid.messaging.Sender
    :ivar receiver: A message sender.
    :type receiver: qpid.messaging.Receiver
    """

    def __init__(self, url, name, arguments):
        """
        :param url: The broker url.
        :type url: str
        :param name: The method name.
        :type name: str
        :param arguments: The method arguments.
        :type arguments: dict
        """
        super(Method, self).__init__(url)
        self.name = name
        self.arguments = arguments
        self.connection = Connection(url)
        self.session = None
        self.sender = None
        self.receiver = None
        self.reply_to = REPLY_TO % uuid4()

    @property
    def content(self):
        return {
            '_object_id': OBJECT_ID,
            '_method_name': self.name,
            '_arguments': self.arguments
        }

    @property
    def properties(self):
        return {
            'qmf.opcode': '_method_request',
            'x-amqp-0-10.app-id': 'qmf2',
            'method': 'request'
        }

    def is_open(self):
        """
        Get whether the method is open.
        :return: True if open.
        :rtype: bool
        """
        return self.sender is not None

    def open(self):
        """
        Open a connection and get a sender and receiver.
        """
        if self.is_open():
            # already open
            return
        self.connection.open()
        self.session = self.connection.session()
        self.sender = self.session.sender(ADDRESS)
        self.receiver = self.session.receiver(self.reply_to)

    def repair(self):
        """
        Repair the connection and get a sender and receiver.
        """
        self.close()
        self.connection.close()
        self.connection.open()
        self.session = self.connection.session()
        self.sender = self.session.sender(ADDRESS)
        self.receiver = self.session.receiver(self.reply_to)

    def close(self):
        """
        Close the sender and receiver.
        """
        session = self.session
        self.session = None
        sender = self.sender
        self.sender = None
        receiver = self.receiver
        self.receiver = None
        try:
            receiver.close()
        except Exception:
            pass
        try:
            sender.close()
        except Exception:
            pass
        try:
            session.close()
        except Exception:
            pass

    def on_reply(self, reply):
        """
        Process the QMF reply.
        :param reply: The reply.
        :type reply: Message
        :raise: Error on failures.
        """
        opcode = reply.properties['qmf.opcode']
        if opcode != '_exception':
            # succeeded
            return
        body = reply.content
        values = body['_values']
        code = values['error_code']
        description = values['error_text']
        if code == EEXIST:
            return
        raise Error(description, code)

    @reliable
    def __call__(self):
        """
        Invoke the method.
        :raise: Error on failure.
        """
        self.open()
        try:
            request = Message(
                content=self.content,
                reply_to=self.reply_to,
                properties=self.properties,
                correlation_id=str(uuid4()).encode(),
                subject=SUBJECT)
            self.sender.send(request)
            reply = self.receiver.fetch()
            self.session.acknowledge()
            self.on_reply(reply)
        finally:
            self.close()


class Exchange(BaseExchange):

    def declare(self, url):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'exchange',
            'exchange-type': self.policy,
            'properties': {
                'auto-delete': self.auto_delete,
                'durable': self.durable
            }
        }
        method = Method(url, CREATE, arguments)
        method()

    def delete(self, url):
        """
        Delete the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'exchange',
            'properties': {}
        }
        method = Method(url, DELETE, arguments)
        method()

    def bind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': '/'.join((self.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method = Method(url, CREATE, arguments)
        method()

    def unbind(self, queue, url):
        """
        Unbind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        :raise Error
        """
        arguments = {
            'strict': True,
            'name': '/'.join((self.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method = Method(url, DELETE, arguments)
        method()


class Queue(BaseQueue):

    def declare(self, url):
        """
        Declare the queue.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'queue',
            'properties': {
                'exclusive': self.exclusive,
                'auto-delete': self.auto_delete,
                'durable': self.durable
            }
        }
        method = Method(url, CREATE, arguments)
        method()

    def delete(self, url):
        """
        Delete the queue.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'queue',
            'properties': {}
        }
        method = Method(url, DELETE, arguments)
        method()
