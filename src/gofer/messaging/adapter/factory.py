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

import logging

from gofer.config import get_bool

from gofer.messaging.adapter.descriptor import Descriptor
from gofer.messaging.adapter.url import URL


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# symbols required to be supported by all adapters
REQUIRED = [
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


class AdapterError(Exception):
    pass


class NoAdaptersLoaded(AdapterError):

    DESCRIPTION = 'No messaging adapters loaded'

    def __init__(self):
        AdapterError.__init__(self, NoAdaptersLoaded.DESCRIPTION)


class AdapterNotFound(AdapterError):

    DESCRIPTION = 'Messaging adapter: %s, not-found'

    def __init__(self, name):
        AdapterError.__init__(self, AdapterNotFound.DESCRIPTION % name)
        self.name = name


# --- factory ----------------------------------------------------------------


class Loader:
    """
    Adapter adapter loader.
    :cvar PATH: The default (absolute) path to a directory
        containing descriptors to be loaded.
    :type PATH: str
    :ivar adapters: Loaded adapters.
    :type adapters: dict
    """

    PATH = '/etc/gofer/messaging/adapters'

    def __init__(self):
        self.adapters = {}

    @staticmethod
    def _load(path):
        """
        Load adapters.
        :param path: The absolute path to a directory containing descriptors.
        :type path: str
        :return: The loaded adapters.
        :rtype: dict
        """
        adapters = {}
        for descriptor in Descriptor.load(path):
            if not get_bool(descriptor.main.enabled):
                continue
            package = descriptor.main.package
            try:
                pkg = __import__(package, {}, {}, REQUIRED)
                name = pkg.__name__.split('.')[-1]
                adapters[name] = pkg
                adapters[package] = pkg
                for capability in descriptor.provides:
                    adapters[capability] = pkg
            except (ImportError, AttributeError):
                log.exception(package)
        return adapters

    def load(self, path=PATH):
        """
        Load adapter adapters.
        :param path: The absolute path to a directory containing descriptors.
        :type path: str
        :return: The loaded adapters.
        :rtype: dict
        """
        if not len(self.adapters):
            self.adapters = Loader._load(path)
        return self.adapters


class Adapter(object):

    urls = {}
    loader = Loader()

    @staticmethod
    def bind(url, name):
        adapters = Adapter.loader.load()
        loaded = sorted(adapters)
        if not loaded:
            raise NoAdaptersLoaded()
        try:
            url = URL(url)
            Adapter.urls[url.simple()] = adapters[name]
        except KeyError:
            raise AdapterNotFound(name)

    @staticmethod
    def find(url=None):
        adapters = Adapter.loader.load()
        loaded = sorted(adapters)
        if not loaded:
            raise NoAdaptersLoaded()
        if not url:
            url = loaded[0]
        try:
            url = URL(url)
            if url.adapter:
                return adapters[url.adapter]
            else:
                return Adapter.urls[url.simple()]
        except KeyError:
            return adapters[loaded[0]]
