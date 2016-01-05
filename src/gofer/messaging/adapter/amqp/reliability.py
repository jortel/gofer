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
# Jeff Ortel (jortel@redhat.com)

from time import sleep
from logging import getLogger

from amqp import ChannelError

from gofer.common import Thread, utf8
from gofer.messaging.adapter.model import Messenger, NotFound
from gofer.messaging.adapter.amqp.connection import Connection, CONNECTION_EXCEPTIONS


log = getLogger(__name__)


DELAY = 10  # seconds


def reliable(fn):
    def _fn(messenger, *args, **kwargs):
        repair = lambda: None
        while not Thread.aborted():
            try:
                repair()
                return fn(messenger, *args, **kwargs)
            except ChannelError, le:
                if le.code != 404:
                    log.error(utf8(le))
                    repair = messenger.repair
                    sleep(DELAY)
                else:
                    raise NotFound(*le.args)
            except CONNECTION_EXCEPTIONS, pe:
                log.error(utf8(pe))
                repair = messenger.repair
                sleep(DELAY)
    return _fn


def endpoint(fn):
    def _fn(url):
        _endpoint = Endpoint(url)
        _endpoint.open()
        try:
            return fn(_endpoint)
        finally:
            _endpoint.close()
    return _fn


class Endpoint(Messenger):

    def __init__(self, url):
        super(Endpoint, self).__init__(url)
        self.connection = Connection(url)
        self.channel = None

    def is_open(self):
        return True

    def open(self):
        self.connection.open()
        self.channel = self.connection.channel()
    
    def repair(self):
        self.connection.close()
        self.connection.open()
        self.channel = self.connection.channel()

    def close(self):
        try:
            self.channel.close()
        except Exception:
            pass
