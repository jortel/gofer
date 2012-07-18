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


class Options(object):
    """
    Provides a dict-like object that also provides
    (.) dot notation accessors.
    """

    def __init__(self, *objects, **keywords):
        for obj in objects:
            if isinstance(obj, dict):
                self.__dict__.update(obj)
                continue
            if isinstance(obj, Options):
                self.__dict__.update(obj.__dict__)
                continue
            raise ValueError(obj)
        self.__dict__.update(keywords)
    
    def __getattr__(self, name):
        return self.__dict__.get(name)
    
    def __getitem__(self, name):
        return self.__dict__[name]
    
    def __setitem__(self, name, value):
        self.__dict__[name] = value
        
    def __iadd__(self, obj):
        if isinstance(obj, dict):
            self.__dict__.update(obj)
            return self
        if isinstance(obj, object):
            self.__dict__.update(object.__dict__)
            return self
        raise ValueError(obj)
    
    def __len__(self):
        return len(self.__dict__)
    
    def __iter__(self):
        return iter(self.__dict__)
    
    def __repr__(self):
        return repr(self.__dict__)
    
    def __str__(self):
        return str(self.__dict__)


class Envelope(Options):
    """
    Extends the dict-like object that also provides
    JSON serialization.
    """

    def load(self, s):
        """
        Load using a json string.
        @param s: A json encoded string.
        @type s: str
        """
        d = json.loads(s)
        self.__dict__.update(d)
        return self
    
    def dump(self):
        """
        Dump to a json string.
        @return: A json encoded string.
        @rtype: str
        """
        def fn(obj):
            if isinstance(obj, Options):
                obj = dict(obj.__dict__)
                for k,v in obj.items():
                    obj[k] = fn(v)
                return obj
            if isinstance(obj, dict):
                obj = dict(obj)
                for k,v in obj.items():
                    obj[k] = fn(v)
                return obj
            if isinstance(obj, (tuple, list)):
                obj = [fn(e) for e in obj]
                return obj
            return obj
        d = fn(self)
        return json.dumps(d, indent=2)


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

        
class XBinding:
    """
    Represents an AMQP X-BINDING fragment.
    @ivar exchange: An exchange name.
    @type exchange: str
    @ivar key: An (optional) exchange routing key.
    @type key: str
    """

    def __init__(self, exchange, key=None):
        """
        @param exchange: An exchange name.
        @type exchange: str
        @param key: An (optional) routing key.
        @type key: str
        """
        self.exchange = exchange
        self.key = key
        
    def __str__(self):
        if self.key:
            return "{exchange:%s,key:'%s'}" % (self.exchange, self.key)
        else:
            return "{exchange:%s}" % self.exchange


class XBindings:
    """
    Represents an AMQP X-BINDINGS fragment.
    @ivar bindings: A list of binding object.
    @type bindings: list: L{XBinding}
    """
    
    def __init__(self, bindings=[]):
        """
        @param bindings: A list of binding objects.
        @type bindings: list: L{Binding}
        """
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

    def __init__(self, topic, subject=None):
        """
        @param topic: The name of the topic.
        @type topic: str
        @param subject: The subject.
        @type subject: str
        """
        self.topic = topic
        self.subject = subject

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
    
    def binding(self):
        """
        Get an binding for the queue.
        @return: A binding.
        @rtype: L{XBinding} 
        """
        return XBinding(self.topic, self.subject)

    def __str__(self):
        return self.address()


class Queue(Destination):
    """
    Represents and AMQP queue.
    @ivar name: The name of the queue.
    @type name: str
    @ivar durable: The durable flag.
    @type durable: str
    """

    def __init__(self, name, durable=True, bindings=[]):
        """
        @param name: The name of the queue.
        @type name: str
        @param durable: The durable flag.
        @type durable: str
        @param bindings: An optional list of bindings used to
            bind queues to other exchanges.
        @type bindings: L{Destination}
        """
        self.name = name
        self.durable = durable
        self.bindings = XBindings(bindings)

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
          node:{
            type:queue,
            durable:True,
            %s
          },
          link:{
            durable:True,
            reliability:at-least-once,
            x-subscribe:{exclusive:True}
          }
        }
        """)
        return fmt % (self.name, self.bindings)

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
          node:{
            type:queue,
            %s
          },
          link:{
            durable:True,
            reliability:at-least-once,
            x-subscribe:{exclusive:True}
          }
        }
        """)
        return fmt % (self.name, self.bindings)
    
    def xbinding(self):
        """
        Get an xbinding for the queue.
        @return: An xbinding.
        @rtype: L{XBinding} 
        """
        return XBinding(self.name)

    def __str__(self):
        if self.durable:
            return self.address()
        else:
            return self.tmpAddress()
