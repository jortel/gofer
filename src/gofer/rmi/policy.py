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
Contains request delivery policies.
"""

from gofer.messaging import *
from gofer.rmi.dispatcher import *
from gofer.messaging.consumer import Reader
from logging import getLogger

log = getLogger(__name__)


def timeout(options, none=(None,None)):
    """
    Extract (and default as necessary) the timeout option.
    @param options: Policy options.
    @type options: dict
    @return: The timeout (<start>,<duration>)
    @rtype: tuple
    """
    tm = options.timeout
    if tm is None:
        return none
    if isinstance(tm, (list,tuple)):
        return tm
    return (tm, tm)


class RequestTimeout(Exception):
    """
    Request timeout.
    """

    def __init__(self, sn, index):
        """
        @param sn: The request serial number.
        @type sn: str
        """
        Exception.__init__(self, sn, index)
        
    def sn(self):
        return self.args[0]
    
    def index(self):
        return self.args[1]
        

class RequestMethod:
    """
    Base class for request methods.
    @ivar producer: A queue producer.
    @type producer: L{gofer.messaging.producer.Producer}
    """
    
    def __init__(self, producer):
        """
        @param producer: A queue producer.
        @type producer: L{gofer.messaging.producer.Producer}
        """
        self.producer = producer

    def send(self, address, request, **any):
        """
        Send the request..
        @param address: The destination queue address.
        @type address: str
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        """
        pass

    def broadcast(self, addresses, request, **any):
        """
        Broadcast the request.
        @param addresses: A list of destination queue addresses.
        @type addresses: [str,..]
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        """
        pass


class Synchronous(RequestMethod):
    """
    The synchronous request method.
    This method blocks until a reply is received.
    @ivar reader: A queue reader used to read the reply.
    @type reader: L{gofer.messaging.consumer.Reader}
    """
    
    TIMEOUT = (10, 90)

    def __init__(self, producer, options):
        """
        @param producer: A queue producer.
        @type producer: L{gofer.messaging.producer.Producer}
        @param options: Policy options.
        @type options: dict
        """
        self.timeout = timeout(options, self.TIMEOUT)
        self.queue = Queue(getuuid(), durable=False)
        RequestMethod.__init__(self, producer)

    def send(self, destination, request, **any):
        """
        Send the request then read the reply.
        @param destination: The destination queue address.
        @type destination: str
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        @return: The result of the request.
        @rtype: object
        @raise Exception: returned by the peer.
        """
        sn = self.producer.send(
            destination,
            ttl=self.timeout[0],
            replyto=str(self.queue),
            request=request,
            **any)
        log.info('sent (%s):\n%s', repr(destination), request)
        reader = Reader(self.queue, url=self.producer.url)
        reader.open()
        try:
            self.__getstarted(sn, reader)
            return self.__getreply(sn, reader)
        finally:
            reader.close()

    def __getstarted(self, sn, reader):
        """
        Get the STARTED reply matched by serial number.
        @param sn: The request serial number.
        @type sn: str
        @param reader: A reader.
        @type reader: L{Reader}
        @return: The matched reply envelope.
        @rtype: L{Envelope}
        """
        envelope = reader.search(sn, self.timeout[0])
        if envelope:
            reader.ack()
            if envelope.status:
                log.debug('request (%s), started', sn)
            else:
                self.__onreply(envelope)
        else:
            raise RequestTimeout(sn, 0)

    def __getreply(self, sn, reader):
        """
        Get the reply matched by serial number.
        @param sn: The request serial number.
        @type sn: str
        @param reader: A reader.
        @type reader: L{Reader}
        @return: The matched reply envelope.
        @rtype: L{Envelope}
        """
        envelope = reader.search(sn, self.timeout[1])
        if envelope:
            reader.ack()
            return self.__onreply(envelope)
        else:
            raise RequestTimeout(sn, 1)
        
    def __onreply(self, envelope):
        """
        Handle the reply.
        @param envelope: The reply envelope.
        @type envelope: L{Envelope}
        @return: The matched reply envelope.
        @rtype: L{Envelope}
        """
        reply = Return(envelope.result)
        if reply.succeeded():
            return reply.retval
        else:
            raise RemoteException.instance(reply)


class Asynchronous(RequestMethod):
    """
    The asynchronous request method.
    """

    def __init__(self, producer, options):
        """
        @param producer: A queue producer.
        @type producer: L{gofer.messaging.producer.Producer}
        @param options: Policy options.
        @type options: dict
        """
        RequestMethod.__init__(self, producer)
        self.ctag = options.ctag
        self.timeout = timeout(options)
        self.watchdog = options.watchdog

    def send(self, destination, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param destination: The AMQP destination.
        @type destination: L{Destination}
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        @return: The request serial number.
        @rtype: str
        """
        replyto = self.__replyto()
        sn = self.producer.send(
                destination,
                ttl=self.timeout[0],
                replyto=replyto,
                request=request,
                **any)
        log.info('sent (%s):\n%s', repr(destination), request)
        self.__notifywatchdog(sn, replyto, any)
        return sn

    def broadcast(self, destinations, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param destinations: A list of destinations.
        @type destinations: [L{Destination},..]
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        """
        sns = self.producer.broadcast(
                destinations,
                ttl=self.timeout[0],
                replyto=self.__replyto(),
                request=request,
                **any)
        log.info('sent (%s):\n%s', destinations, request)
        return sns

    def __replyto(self):
        """
        Get replyto based on the correlation I{tag}.
        @return: The replyto AMQP address.
        @rtype: str
        """
        if self.ctag:
            queue = Queue(self.ctag)
            return str(queue)
        else:
            return None

    def __notifywatchdog(self, sn, replyto, any):
        """
        Add the request to the I{watchdog} for tacking.
        @param sn: A serial number.
        @type sn: str
        @param replyto: An AMQP address.
        @type replyto: str
        @param any: User defined data.
        @type any: any
        """
        any = Envelope(any)
        if replyto and \
           self.ctag and \
           self.timeout[0] is not None and \
           self.timeout[1] is not None and \
           self.watchdog is not None:
            self.watchdog.track(
                sn, 
                replyto,
                any.any,
                self.timeout)
        