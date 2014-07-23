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

import os
import logging

from gofer.transport.url import URL


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# __package__ not supported in python 2.4
PACKAGE = '.'.join(__name__.split('.')[:-1])

# symbols required to be provided by all transports
REQUIRED = [
    'PROVIDES',
    'Exchange',
    'Broker',
    'Endpoint',
    'Queue',
    'Producer',
    'BinaryProducer',
    'Reader',
    'send',
]


# --- exceptions -------------------------------------------------------------


class TransportError(Exception):
    pass


class NoTransportsLoaded(TransportError):

    DESCRIPTION = 'No transports loaded'

    def __str__(self):
        return self.DESCRIPTION


class TransportNotFound(TransportError):

    DESCRIPTION = 'Transport: %s, not-found'

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.DESCRIPTION % self.name


# --- factory ----------------------------------------------------------------


class Loader:
    """
    Transport plugin loader.
    :ivar plugins: Loaded plugins.
    :type plugins: dict
    """

    def __init__(self):
        self.plugins = {}

    @staticmethod
    def _load():
        """
        Load transport plugins.
        :return: The loaded plugins.
        :rtype: dict
        """
        plugins = {}
        _dir = os.path.dirname(__file__)
        for name in os.listdir(_dir):
            path = os.path.join(_dir, name)
            if not os.path.isdir(path):
                continue
            try:
                package = '.'.join((PACKAGE, name))
                pkg = __import__(package, {}, {}, REQUIRED)
                plugins[name] = pkg
                plugins[package] = pkg
                for capability in pkg.PROVIDES:
                    plugins[capability] = pkg
            except (ImportError, AttributeError),e:
                log.exception(path)
        return plugins

    def load(self):
        """
        Load transport plugins.
        :return: The loaded plugins.
        :rtype: dict
        """
        if not len(self.plugins):
            self.plugins = Loader._load()
        return self.plugins


class Transport(object):

    urls = {}
    loader = Loader()

    @staticmethod
    def bind(url, name):
        plugins = Transport.loader.load()
        loaded = sorted(plugins)
        if not loaded:
            raise NoTransportsLoaded()
        try:
            url = URL(url)
            Transport.urls[url.simple()] = plugins[name]
        except KeyError:
            raise TransportNotFound(name)

    @staticmethod
    def find(url=None):
        plugins = Transport.loader.load()
        loaded = sorted(plugins)
        if not loaded:
            raise NoTransportsLoaded()
        if not url:
            url = loaded[0]
        try:
            url = URL(url)
            if url.transport:
                return plugins[url.transport]
            else:
                return plugins[url.simple()]
        except KeyError:
            return plugins[loaded[0]]
