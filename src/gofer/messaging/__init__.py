#
# Copyright (c) 2011 Red Hat, Inc.
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

import string
from uuid import uuid4
import simplejson as json

version = '0.4'


def getuuid():
    return str(uuid4())

def squash(s):
    sq = []
    for c in s:
        if c in string.whitespace:
            continue
        sq.append(c)
    return ''.join(sq)

class Options(dict):
    """
    Container options.
    Options:
      - async : Indicates that requests asynchronous.
          Default = False
      - ctag : The asynchronous correlation tag.
          When specified, it implies all requests are asynchronous.
      - window : The request window.  See I{Window}.
          Default = any time.
      - secret : A shared secret used for request authentication.
      - timeout : The request timeout (seconds).
          Default = (10,90) seconds.
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__= dict.__delitem__


class Envelope(dict):
    """
    Basic envelope is a json encoded/decoded dictionary
    that provides dot (.) style access.
    """

    __getattr__ = dict.get
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

    def load(self, s):
        """
        Load using a json string.
        @param s: A json encoded string.
        @type s: str
        """
        d = json.loads(s)
        self.update(d)
        return self

    def dump(self):
        """
        Dump to a json string.
        @return: A json encoded string.
        @rtype: str
        """
        d = self
        return json.dumps(d, indent=2)

    def __str__(self):
        return self.dump()


class Destination:
    """
    AMQP destinations (topics & queues)
    """

    def address(self):
        """
        Get the destination I{formal} AMQP address which contains
        properties used to create the destination.
        @return: The destination address.
        @rtype: str
        """
        pass

    def delete(self, session):
        """
        Delete the destination.
        Implemented using a hack becauase python API does not
        directly support removing destinations.
        @param session: An AMQP session.
        @type session: I{qpid.messaging.Session}
        """
        address = '%s;{delete:always}' % repr(self)
        sender = session.sender(address)
        sender.close()

    def __repr__(self):
        return str(self).split(';', 1)[0]


class Topic(Destination):
    """
    Represents and AMQP topic.
    @ivar topic: The name of the topic.
    @type topic: str
    @ivar subject: The subject.
    @type subject: str
    @ivar name: The (optional) subscription name.
        Used for durable subscriptions.
    @type name: str
    """

    def __init__(self, topic, subject=None, name=None):
        """
        @param topic: The name of the topic.
        @type topic: str
        @param subject: The subject.
        @type subject: str
        @param name: The (optional) subscription name.
            Used for durable subscriptions.
        @type name: str
        """
        self.topic = topic
        self.subject = subject
        self.name = name

    def address(self):
        """
        Get the topic I{formal} AMQP address which contains
        properties used to create the topic.
        @return: The topic address.
        @rtype: str
        """
        fmt = squash("""
        %s;{
          create:always,
          node:{type:topic},
          link:{
            x-declare:{
              auto-delete:True,
              arguments:{no-local:True}
            }
          }
        }
        """)
        topic = self.topic
        if self.subject:
            topic = '/'.join((topic, self.subject))
        return fmt % topic

    def queuedAddress(self):
        """
        Get the topic I{durable} AMQP address which contains
        properties used to create the topic.
        @return: The topic address.
        @rtype: str
        """
        fmt = squash("""
        %s;{
          create:always,
          node:{type:topic,durable:True},
          link:{
            durable:True,
            x-declare:{
              arguments:{no-local:True}
            },
            x-bindings:[
              {exchange:%s
               %s}
            ]
          }
        }
        """)
        topic = self.topic
        if self.subject:
            key = ',key:%s' % self.subject
        else:
            key = ''
        return fmt % (self.name, self.topic, key)

    def __str__(self):
        if self.name:
            return self.queuedAddress()
        else:
            return self.address()


class Queue(Destination):
    """
    Represents and AMQP queue.
    @ivar name: The name of the queue.
    @type name: str
    @ivar durable: The durable flag.
    @type durable: str
    """

    def __init__(self, name, durable=True):
        """
        @param name: The name of the queue.
        @type name: str
        @param durable: The durable flag.
        @type durable: str
        """
        self.name = name
        self.durable = durable

    def address(self):
        """
        Get the queue I{formal} AMQP address which contains
        properties used to create the queue.
        @return: The queue address.
        @rtype: str
        """
        fmt = squash("""
        %s;{
          create:always,
          node:{type:queue,durable:True},
          link:{
            durable:True,
            x-subscribe:{exclusive:True}
          }
        }
        """)
        return fmt % self.name

    def tmpAddress(self):
        """
        Get the queue AMQP address which contains
        properties used to create a temporary queue.
        @return: The queue address.
        @rtype: str
        """
        fmt = squash("""
        %s;{
          create:always,
          delete:receiver,
          node:{type:queue},
          link:{
            durable:True,
            x-subscribe:{exclusive:True}
          }
        }
        """)
        return fmt % self.name

    def __str__(self):
        if self.durable:
            return self.address()
        else:
            return self.tmpAddress()
