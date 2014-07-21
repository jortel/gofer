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

from logging import getLogger

from gofer.transport.amqplib import endpoint

from gofer.transport.model import BaseExchange, BaseQueue, Destination


log = getLogger(__name__)


# --- constants --------------------------------------------------------------


EXPIRES = {'x-expires': 10000}


# --- reconnect decorator ----------------------------------------------------


def reliable(fn):
    return endpoint.endpoint(endpoint.reliable(fn))


# --- model ------------------------------------------------------------------


class Exchange(BaseExchange):

    def declare(self, url):
        @reliable
        def _fn(_endpoint):
            if self.auto_delete:
                arguments = EXPIRES
            else:
                arguments = None
            channel = _endpoint.channel()
            channel.exchange_declare(
                self.name,
                self.policy,
                durable=self.durable,
                auto_delete=self.auto_delete,
                arguments=arguments)
        _fn(url)

    def delete(self, url):
        @reliable
        def _fn(_endpoint):
            channel = _endpoint.channel()
            channel.exchange_delete(self.name, nowait=True)
        _fn(url)


class Queue(BaseQueue):

    def __init__(self, name, exchange=None, routing_key=None):
        BaseQueue.__init__(
            self,
            name,
            exchange=exchange or Exchange(''),
            routing_key=routing_key or name)

    def declare(self, url):
        @reliable
        def _fn(_endpoint):
            channel = _endpoint.channel()
            if self.auto_delete:
                arguments = EXPIRES
            else:
                arguments = None
            channel.queue_declare(
                self.name,
                durable=self.durable,
                auto_delete=self.auto_delete,
                exclusive=self.exclusive,
                arguments=arguments)
            if self.exchange != Exchange(''):
                channel.queue_bind(
                    self.name,
                    exchange=self.exchange.name,
                    routing_key=self.routing_key)
        _fn(url)

    def delete(self, url):
        @reliable
        def _fn(_endpoint):
            channel = _endpoint.channel()
            channel.queue_delete(self.name, nowait=True)
        _fn(url)

    def destination(self, url):
        """
        Get a destination object for the node.
        :return: A destination for the node.
        :rtype: Destination
        """
        return Destination(routing_key=self.routing_key, exchange=self.exchange.name)

