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

from qpidtoollibs import BrokerAgent

from gofer.messaging.adapter.model import BaseExchange, BaseQueue

from gofer.messaging.adapter.qpid.connection import Connection


class Broker(BrokerAgent):
    """
    Broker Agent.
    """

    def __init__(self, url):
        """
        :param url: A broker URL.
        :type url: str
        """
        self._connection = Connection(url)
        self._connection.open()
        super(Broker, self).__init__(self._connection.impl)

    def close(self):
        """
        Close the agent.
        """
        BrokerAgent.close(self)
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


class Exchange(BaseExchange):
    """
    A qpid AMQP exchange.
    """

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        BaseExchange.__init__(self, name, policy=policy)

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        broker = Broker(url)
        try:
            options = {
                'durable': self.durable,
                'auto-delete': self.auto_delete
            }
            try:
                broker.addExchange(self.policy, self.name, options)
            except Exception, e:
                # already created
                if ': 7' in str(e):
                    pass
        finally:
            broker.close()

    def delete(self, url):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        broker = Broker(url)
        try:
            broker.delExchange(self.name)
        finally:
            broker.close()

    def bind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: Queue
        """
        broker = Broker(url)
        try:
            key = queue.name
            broker.bind(self.name, queue.name, key)
        finally:
            broker.close()

    def unbind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        """
        broker = Broker(url)
        try:
            key = queue.name
            broker.unbind(self.name, queue.name, key)
        finally:
            broker.close()


class Queue(BaseQueue):
    """
    A qpid AMQP queue.
    """

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        broker = Broker(url)
        try:
            options = {
                'durable': self.durable,
                'auto-delete': self.auto_delete,
                'exclusive': self.exclusive
            }
            try:
                broker.addQueue(self.name, options)
            except Exception, e:
                # already created
                if ': 7' in str(e):
                    pass
        finally:
            broker.close()

    def delete(self, url):
        """
        Delete the node.
        :param url: The broker URL.
        :type url: str
        :raise: ModelError
        """
        broker = Broker(url)
        try:
            broker.delQueue(self.name)
        finally:
            broker.close()
