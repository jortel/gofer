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

from gofer.messaging.adapter.amqplib import endpoint

from gofer.messaging.adapter.model import BaseExchange, BaseQueue


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

    def bind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        @reliable
        def _fn(_endpoint):
            key = queue.name
            channel = _endpoint.channel()
            channel.queue_bind(queue.name, exchange=self.name, routing_key=key)
        _fn(url)

    def unbind(self, queue, url):
        """
        Unbind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        """
        @reliable
        def _fn(_endpoint):
            key = queue.name
            channel = _endpoint.channel()
            channel.queue_unbind(queue.name, exchange=self.name, routing_key=key)
        _fn(url)


class Queue(BaseQueue):

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
        _fn(url)

    def delete(self, url):
        @reliable
        def _fn(_endpoint):
            channel = _endpoint.channel()
            channel.queue_delete(self.name, nowait=True)
        _fn(url)
