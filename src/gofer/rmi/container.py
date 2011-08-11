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


"""
Agent base classes.
"""

from gofer.messaging import *
from gofer.rmi.stub import Stub
from gofer.rmi.window import Window
from logging import getLogger

log = getLogger(__name__)

        
class Container:
    """
    The stub container
    @ivar __id: The peer ID.
    @type __id: str
    @ivar __producer: An AMQP producer.
    @type __producer: L{gofer.messaging.producer.Producer}
    @ivar __options: Container options.
    @type __options: L{Options}
    """

    def __init__(self, uuid, producer, **options):
        """
        @param uuid: The peer ID.
        @type uuid: str
        @param producer: An AMQP producer.
        @type producer: L{gofer.messaging.producer.Producer}
        @param options: keyword options.
        @type options: dict
        """
        self.__id = uuid
        self.__producer = producer
        self.__options = Options(window=Window())
        self.__options.update(options)

    def __destination(self):
        """
        Get the stub destination(s).
        @return: Either a queue destination or a list of queues.
        @rtype: list
        """
        if isinstance(self.__id, (list,tuple)):
            queues = []
            for d in self.__id:
                queues.append(Queue(d))
            return queues
        else:
            return Queue(self.__id)
    
    def __getattr__(self, name):
        """
        Get a stub by name.
        @param name: The name of a stub class.
        @type name: str
        @return: A stub object.
        @rtype: L{Stub}
        """
        return Stub.stub(
            name,
            self.__producer,
            self.__destination(),
            self.__options)

    def __str__(self):
        return '{%s} opt:%s' % (self.__id, str(self.__options))
    
    def __repr__(self):
        return str(self)
