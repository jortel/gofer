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


# routing key
ROUTE_ALL = '#'

# exchange types
DIRECT = 'direct'
TOPIC = 'topic'


class Node(object):
    """
    An AMQP node.
    :ivar name: The node name.
    :type name: str
    """

    def __init__(self, name):
        """
        :param name: The node name.
        :type name: str
        """
        self.name = name

    def declare(self, url):
        """
        Declare the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        pass

    def delete(self, url):
        """
        Delete the node.
        :param url: The peer URL.
        :type url: str
        :return: self
        """
        pass


class Exchange(Node):
    """
    An AMQP exchange.
    :ivar policy: The routing policy (direct|topic|..).
    :type policy: str
    :ivar durable: Indicates the exchange is durable.
    :type durable: bool
    :ivar auto_delete: The exchange is auto deleted.
    :type auto_delete: bool
    """

    def __init__(self, name, policy=None):
        """
        :param name: The exchange name.
        :type name: str
        :param policy: The routing policy (direct|topic|..).
        :type policy: str
        """
        Node.__init__(self, name)
        self.policy = policy
        self.durable = True
        self.auto_delete = False

    def __eq__(self, other):
        return isinstance(other, Exchange) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)


class Destination(object):
    """
    An AMQP destination.
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar exchange: An (optional) AMQP exchange.
    :type exchange: str
    """

    ROUTING_KEY = 'routing_key'
    EXCHANGE = 'exchange'

    @staticmethod
    def create(d):
        return Destination(d[Destination.ROUTING_KEY], d[Destination.EXCHANGE])

    def __init__(self, routing_key, exchange=''):
        """
        :param exchange: An AMQP exchange.
        :type exchange: str
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        self.routing_key = routing_key
        self.exchange = exchange

    def dict(self):
        return {
            Destination.ROUTING_KEY: self.routing_key,
            Destination.EXCHANGE: self.exchange,
        }

    def __eq__(self, other):
        return isinstance(other, Destination) and \
            self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)


class Queue(Node):
    """
    An AMQP queue.
    :ivar exchange: An AMQP exchange.
    :type exchange: Exchange
    :ivar routing_key: Message routing key.
    :type routing_key: str
    :ivar durable: Indicates the queue is durable.
    :type durable: bool
    :ivar auto_delete: The queue is auto deleted.
    :type auto_delete: bool
    :ivar exclusive: Indicates the queue can only have one consumer.
    :type exclusive: bool
    """

    def __init__(self, name, exchange=None, routing_key=None):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: Exchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        Node.__init__(self, name)
        self.exchange = exchange
        self.routing_key = routing_key
        self.durable = True
        self.auto_delete = False
        self.exclusive = False

    def destination(self):
        """
        Get a destination object for the node.
        :return: A destination for the node.
        :rtype: Destination
        """
        return Destination(self.routing_key, exchange=self.exchange.name)

    def __eq__(self, other):
        return isinstance(other, Queue) and \
            self.name == other.name

    def __ne__(self, other):
        return not (self == other)
