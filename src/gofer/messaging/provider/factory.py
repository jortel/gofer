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

from gofer.config import get_bool

from gofer.messaging.provider.descriptor import Descriptor
from gofer.messaging.provider.url import URL


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# symbols required to be supported by all providers
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


class ProviderError(Exception):
    pass


class NoProvidersLoaded(ProviderError):

    DESCRIPTION = 'No messaging providers loaded'

    def __init__(self):
        ProviderError.__init__(self, NoProvidersLoaded.DESCRIPTION)


class ProviderNotFound(ProviderError):

    DESCRIPTION = 'Messaging provider: %s, not-found'

    def __init__(self, name):
        ProviderError.__init__(self, ProviderNotFound.DESCRIPTION % name)
        self.name = name


# --- factory ----------------------------------------------------------------


class Loader:
    """
    Provider provider loader.
    :ivar providers: Loaded providers.
    :type providers: dict
    """

    def __init__(self):
        self.providers = {}

    @staticmethod
    def _load():
        """
        Load providers.
        :return: The loaded providers.
        :rtype: dict
        """
        providers = {}
        for descriptor in Descriptor.load():
            if not get_bool(descriptor.main.enabled):
                continue
            package = descriptor.main.provider
            try:
                pkg = __import__(package, {}, {}, REQUIRED)
                name = pkg.__name__.split('.')[-1]
                providers[name] = pkg
                providers[package] = pkg
                for capability in descriptor.provides:
                    providers[capability] = pkg
            except (ImportError, AttributeError):
                log.exception(package)
        return providers

    def load(self):
        """
        Load provider providers.
        :return: The loaded providers.
        :rtype: dict
        """
        if not len(self.providers):
            self.providers = Loader._load()
        return self.providers


class Provider(object):

    urls = {}
    loader = Loader()

    @staticmethod
    def bind(url, name):
        providers = Provider.loader.load()
        loaded = sorted(providers)
        if not loaded:
            raise NoProvidersLoaded()
        try:
            url = URL(url)
            Provider.urls[url.simple()] = providers[name]
        except KeyError:
            raise ProviderNotFound(name)

    @staticmethod
    def find(url=None):
        providers = Provider.loader.load()
        loaded = sorted(providers)
        if not loaded:
            raise NoProvidersLoaded()
        if not url:
            url = loaded[0]
        try:
            url = URL(url)
            if url.provider:
                return providers[url.provider]
            else:
                return Provider.urls[url.simple()]
        except KeyError:
            return providers[loaded[0]]
