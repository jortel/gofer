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

from gofer.messaging.provider.url import URL


log = logging.getLogger(__name__)


# --- constants --------------------------------------------------------------

# __package__ not supported in python 2.4
PACKAGE = '.'.join(__name__.split('.')[:-1])

# symbols required to be supported by all providers
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


class ProviderError(Exception):
    pass


class NoProvidersLoaded(ProviderError):

    DESCRIPTION = 'No messaging providers loaded'

    def __str__(self):
        return self.DESCRIPTION


class ProviderNotFound(ProviderError):

    DESCRIPTION = 'Messaging provider: %s, not-found'

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.DESCRIPTION % self.name


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
        Load provider providers.
        :return: The loaded providers.
        :rtype: dict
        """
        providers = {}
        _dir = os.path.dirname(__file__)
        for name in os.listdir(_dir):
            path = os.path.join(_dir, name)
            if not os.path.isdir(path):
                continue
            try:
                package = '.'.join((PACKAGE, name))
                pkg = __import__(package, {}, {}, REQUIRED)
                providers[name] = pkg
                providers[package] = pkg
                for capability in pkg.PROVIDES:
                    providers[capability] = pkg
            except (ImportError, AttributeError),e:
                log.exception(path)
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
                return providers[url.simple()]
        except KeyError:
            return providers[loaded[0]]
