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

log = getLogger(__name__)


class MetaBroker(Singleton):
    """
    Broker MetaClass.
    Singleton by simple url.
    """

    @classmethod
    def key(mcs, t, d):
        url = t[0]
        if not isinstance(url, URL):
            url = URL(url)
        return url.simple()


class Broker:
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
    :ivar virtual_host: The AMQP virtual host.
    :type virtual_host: str
    """

    __metaclass__ = MetaBroker

    def __init__(self, url):
        """
        :param url: The broker url <transport>://<host>:<port>.
        :type url: str
        """
        if isinstance(url, URL):
            self.url = url
        else:
            self.url = URL(url)
        self.connection = Local()
        self.virtual_host = None
        self.cacert = None
        self.clientcert = None
        self.host_validation = False
        self.userid = None
        self.password = None

    def id(self):
        """
        Get broker identifier.
        :return: The broker *simple* url.
        :rtype: str
        """
        return self.url.simple()

    def connect(self):
        """
        Connect to the broker.
        :return: The AMQP connection object.
        :rtype: *Connection*
        """
        raise NotImplemented()

    def close(self):
        """
        Close the connection to the broker.
        """
        raise NotImplemented()

    def __str__(self):
        s = []
        s.append('{%s}:' % self.id())
        s.append('transport=%s' % self.url.transport.upper())
        s.append('host=%s' % self.url.host)
        s.append('port=%d' % self.url.port)
        s.append('cacert=%s' % self.cacert)
        s.append('clientcert=%s' % self.clientcert)
        s.append('userid=%s' % self.userid)
        s.append('password=%s' % self.password)
        return '\n'.join(s)


class URL:
    """
    Represents a broker URL.
    :ivar transport: A URL transport.
    :type transport: str
    :ivar host: The host.
    :type host: str
    :ivar port: The tcp port.
    :type port: int
    """

    SSL = ('ssl', 'amqps')

    @staticmethod
    def split(s):
        """
        Split the url string.
        :param s: A url string format: <transport>://<host>:<port>.
        :type s: str
        :return: The url parts: (transport, host, port)
        :rtype: tuple
        """
        transport, hp = URL.split_url(s)
        host, port = URL.split_port(hp, URL._port(transport))
        return transport, host, port

    @staticmethod
    def split_url(s):
        """
        Split the transport and url parts.
        :param s: A url string format: <transport>://<host>:<port>.
        :type s: str
        :return: The urlparts: (transport, hostport)
        :rtype: tuple
        """
        part = s.split('://', 1)
        if len(part) > 1:
            transport, hp = (part[0], part[1])
        else:
            transport, hp = ('tcp', part[0])
        return transport, hp

    @staticmethod
    def split_port(s, default):
        """
        Split the host and port.
        :param s: A url string format: <host>:<port>.
        :type s: str
        :return: The urlparts: (host, port)
        :rtype: tuple
        """
        part = s.split(':')
        host = part[0]
        if len(part) < 2:
            port = default
        else:
            port = part[1]
        return host, int(port)

    @staticmethod
    def _port(transport):
        """
        Get the port based on the transport.
        :param transport: The URL transport or scheme.
        :type transport: str
        :return: port
        :rtype: int
        """
        if transport.lower() in URL.SSL:
            return 5671
        else:
            return 5672

    def __init__(self, s):
        """
        :param s: A url string format: <transport>://<host>:<port>.
        :type s: str
        """
        self.transport, self.host, self.port = self.split(s)

    def simple(self):
        """
        Get the *simple* string representation: <host>:<port>
        :return: "<host>:<port>"
        :rtype: str
        """
        return '%s:%d' % (self.host, self.port)

    def is_ssl(self):
        return self.transport.lower() in self.SSL

    def __hash__(self):
        return hash(self.simple())

    def __eq__(self, other):
        return self.simple() == other.simple()

    def __str__(self):
        return '%s://%s:%d' % \
            (self.transport,
             self.host,
             self.port)
