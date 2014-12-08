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


import string

from gofer.messaging.adapter.qpid.endpoint import Endpoint

from gofer.messaging.adapter.model import BaseExchange, BaseQueue, Destination


# --- utils ------------------------------------------------------------------


def squash(s):
    """
    Squash the string by stripping white space.
    :param s: A string to squash.
    :type s: str
    :return: The squashed string.
    :rtype: str
    """
    sq = []
    for c in s:
        if c in string.whitespace:
            continue
        sq.append(c)
    return ''.join(sq)


# --- model ------------------------------------------------------------------


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

    def address(self):
        """
        Get the *special* qpid messaging address string.
        :return: The qpid address string.
        :rtype: str
        """
        fmt = squash("""
        %(name)s;{
          create:always,
          node:{
            type:topic,
            durable:%(durable)s,
            x-declare:{exchange:'%(name)s',type:%(policy)s}
          }
        }
        """)
        args = dict(name=self.name, durable=self.durable, policy=self.policy)
        return fmt % args

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        if not self.policy:
            return
        endpoint = Endpoint(url)
        endpoint.open()
        try:
            session = endpoint.channel()
            sender = session.sender(self.address())
            sender.close()
        finally:
            endpoint.close()


class Queue(BaseQueue):
    """
    A qpid AMQP queue.
    """

    def __init__(self, name, exchange=None, routing_key=None):
        """
        :param name: The queue name.
        :type name: str
        :param exchange: An AMQP exchange
        :type exchange: BaseExchange
        :param routing_key: Message routing key.
        :type routing_key: str
        """
        BaseQueue.__init__(
            self,
            name,
            exchange=exchange or Exchange(''),
            routing_key=routing_key or name)

    def bindings(self):
        """
        Get the *x-bindings* part of the address.
        :return: The bindings part.
        :rtype: str
        """
        if self.exchange != Exchange(''):
            binding = XBinding(self.exchange, self.routing_key)
            return XBindings(binding)
        else:
            return XBindings()

    def x_declare(self):
        """
        Get the *x-declare* part of the address.
        :return: The bindings part.
        :rtype: str
        """
        if self.auto_delete:
            return squash("""
                x-declare:{
                  auto-delete:True,
                  arguments:{'qpid.auto_delete_timeout':10}
                },
            """)
        else:
            return ''

    def address(self):
        """
        Get the *special* qpid messaging address string.
        :return: The qpid address string.
        :rtype: str
        """
        if self.durable:
            fmt = squash("""
            %(name)s;{
              create:always,
              node:{
                type:queue,
                durable:True,
                %(x_declare)s
                %(x_bindings)s
              },
              link:{
                durable:True,
                reliability:at-least-once,
                x-subscribe:{exclusive:%(exclusive)s}
              }
            }
            """)
        else:
            fmt = squash("""
            %(name)s;{
              create:always,
              delete:receiver,
              node:{
                type:queue,
                durable:False,
                %(x_declare)s
                %(x_bindings)s
              },
              link:{
                durable:True,
                reliability:at-least-once,
                x-subscribe:{exclusive:%(exclusive)s}
              }
            }
            """)
        args = dict(
            name=self.name,
            x_declare=self.x_declare(),
            x_bindings=self.bindings(),
            exclusive=self.exclusive)
        return fmt % args

    def declare(self, url):
        """
        Declare the node.
        :param url: The broker URL.
        :type url: str
        """
        endpoint = Endpoint(url)
        endpoint.open()
        try:
            session = endpoint.channel()
            sender = session.sender(self.address())
            sender.close()
        finally:
            endpoint.close()

    def destination(self, url):
        """
        Get a destination object for the node.
        :return: A destination for the node.
        :rtype: Destination
        """
        return Destination(routing_key=self.routing_key, exchange=self.exchange.name)

    def __str__(self):
        return self.address()


# --- bindings ---------------------------------------------------------------


class XBinding:

    def __init__(self, exchange, routing_key=None):
        self.exchange = exchange.name
        self.routing_key = routing_key

    def __str__(self):
        if self.routing_key:
            return "{exchange:'%s',key:'%s'}" % (self.exchange, self.routing_key)
        else:
            return "{exchange:'%s'}" % self.exchange


class XBindings:

    def __init__(self, *bindings):
        self.bindings = bindings

    def __bindings(self):
        bindings = []
        i = 0
        for b in self.bindings:
            if i > 0:
                bindings.append(',')
            bindings.append(str(b))
            i += 1
        return ''.join(bindings)

    def __str__(self):
        if self.bindings:
            return 'x-bindings:[%s]' % self.__bindings()
        else:
            return ''