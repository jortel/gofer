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
Defined AMQP broker objects.
"""

from logging import getLogger
from threading import local as Local

from gofer import Singleton
from gofer.transport.url import URL
from gofer.transport.binder import Binder

log = getLogger(__name__)


DEFAULT_URL = 'amqp://localhost'


class BaseBroker(object):
    """
    Represents an AMQP broker.
    :ivar connection: A thread local containing an open connection.
    :type connection: Local
    :ivar url: The broker's url.
    :type url: URL
    :ivar cacert: Path to a PEM encoded file containing
        the CA certificate used to validate the server certificate.
    :type cacert: str
    :ivar clientcert: Path to a PEM encoded file containing
        the private key & certificate used for client authentication.
    :type clientcert: str
    :ivar host_validation: Enable SSL host validation.
    :type host_validation: bool
    """

    def __init__(self, url):
        """
        :param url: The broker url:
            <transport>+<scheme>://<userid:password@<host>:<port>/<virtual-host>.
        :type url: str|URL
        """
        if not isinstance(url, URL):
            url = URL(url)
        self.url = url
        self.connection = Local()
        self.cacert = None
        self.clientcert = None
        self.host_validation = False

    def id(self):
        return self.url.simple()

    @property
    def transport(self):
        """
        Get the (gofer) transport component of the url.
        :return: The transport component.
        :rtype: str
        """
        return self.url.transport

    @property
    def scheme(self):
        """
        Get the scheme component of the url.
        :return: The scheme component.
        :rtype: str
        """
        return self.url.scheme

    @property
    def host(self):
        """
        Get the host component of the url.
        :return: The host component.
        :rtype: str
        """
        return self.url.host

    @property
    def port(self):
        """
        Get the port component of the url.
        :return: The port component.
        :rtype: str
        """
        return self.url.port

    @property
    def userid(self):
        """
        Get the userid component of the url.
        :return: The userid component.
        :rtype: str
        """
        return self.url.userid

    @property
    def password(self):
        """
        Get the password component of the url.
        :return: The password component.
        :rtype: str
        """
        return self.url.password

    @property
    def virtual_host(self):
        """
        Get the virtual_host component of the url.
        :return: The virtual_host component.
        :rtype: str
        """
        return self.url.path

    def __str__(self):
        s = list()
        s.append('url=%s' % self.url)
        s.append('cacert=%s' % self.cacert)
        s.append('clientcert=%s' % self.clientcert)
        s.append('host-validation=%s' % self.host_validation)
        return '|'.join(s)


class BrokerSingleton(Singleton):
    """
    Broker MetaClass.
    Singleton by simple url.
    """

    @classmethod
    def key(mcs, t, d):
        url = t[0]
        if isinstance(url, str):
            url = URL(url)
        if not isinstance(url, URL):
            raise ValueError('url must be: str|URL')
        return url.simple()

    def __call__(cls, *args, **kwargs):
        if not args:
            args = (DEFAULT_URL,)
        return Singleton.__call__(cls, *args, **kwargs)


class Broker(BaseBroker):
    """
    Represents an AMQP broker.
    """

    __metaclass__ = BrokerSingleton

    def __init__(self, url=None):
        """
        :param url: The broker url:
            <transport>+<scheme>://<userid:password@<host>:<port>/<virtual-host>.
        :type url: str|URL
        """
        BaseBroker.__init__(self, url)
        plugin = Binder.find(url)
        self._impl = plugin.Broker(url)

    def connect(self):
        """
        Connect to the broker.
        :return: The AMQP connection object.
        :rtype: *Connection*
        """
        self._impl.cacert = self.cacert
        self._impl.clientcert = self.cacert
        self._impl.host_validation = self.host_validation
        self._impl.connect()

    def close(self):
        """
        Close the connection to the broker.
        """
        self._impl.close()
