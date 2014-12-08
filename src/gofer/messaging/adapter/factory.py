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

from gofer.messaging.model import ModelError
from gofer.messaging.adapter.descriptor import Descriptor
from gofer.messaging.adapter.url import URL


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# symbols required to be supported by all adapters
REQUIRED = [
    'Connection',
    'Endpoint',
    'Exchange',
    'Queue',
    'Producer',
    'BinaryProducer',
    'Reader',
    'send',
]


# --- exceptions -------------------------------------------------------------


class AdapterError(ModelError):
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
    :ivar list: A list of loaded adapters.
    :type list: list
    :ivar catalog: A catalog of loaded adapters by capabilities.
    :type catalog: dict
    """

    PATH = '/etc/gofer/messaging/adapters'

    def __init__(self):
        self.list = []
        self.catalog = {}

    @staticmethod
    def _load(path):
        """
        Load the adapters and return a list and catalog.
        :param path: The absolute path to a directory containing descriptors.
        :type path: str
        :return: A tuple of (list, dict)
        :rtype: tuple
        """
        _list = []
        catalog = {}
        for descriptor in Descriptor.load(path):
            if not get_bool(descriptor.main.enabled):
                continue
            package = descriptor.main.package
            try:
                pkg = __import__(package, {}, {}, REQUIRED)
                name = pkg.__name__.split('.')[-1]
                _list.append(pkg)
                catalog[name] = pkg
                catalog[package] = pkg
                for capability in descriptor.provides:
                    catalog[capability] = pkg
            except (ImportError, AttributeError):
                log.exception(package)
        return _list, catalog

    def load(self, path=PATH):
        """
        Load adapter adapters.
        :param path: The absolute path to a directory containing descriptors.
        :type path: str
        :return: The loaded adapters.
        :rtype: dict
        """
        if not self.list:
            _list, catalog = Loader._load(path)
            self.list = _list
            self.catalog = catalog
        return self.list, self.catalog


class Adapter(object):
    """
    A messaging adapter factory object.
    :cvar bindings: A mapping of URL to adapter.
    :type bindings: dict
    :cvar loader: An adapter loader.
    :type loader: Loader
    """

    bindings = {}
    loader = Loader()

    @staticmethod
    def bind(url, name):
        """
        Bind (associate) a URL to an adapter.
        :param url: A broker URL.
        :type url: str
        :param name: An adapter name or capability.
        :type name: str
        :raises: KeyError
        """
        _list, catalog = Adapter.loader.load()
        if not _list:
            raise NoAdaptersLoaded()
        try:
            url = URL(url)
            Adapter.bindings[url.simple()] = catalog[name]
        except KeyError:
            raise AdapterNotFound(name)

    @staticmethod
    def find(url=None):
        """
        Find an adapter by URL.
        :param url: A broker URL.
        :type url: str
        :return: The requested adapter or the adapter with the
            highest *priority*.
        """
        _list, catalog = Adapter.loader.load()
        if not _list:
            raise NoAdaptersLoaded()
        if not url:
            return _list[0]
        try:
            url = URL(url)
            if url.adapter:
                return catalog[url.adapter]
            else:
                return Adapter.bindings[url.simple()]
        except KeyError:
            return _list[0]

