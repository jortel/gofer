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
Defined URL objects.
"""


class URL:
    """
    Represents a broker URL.
    Format: <adapter>+<scheme>://<user>:<password>@<host>:<port></>.
    :ivar adapter: A URL adapter.
    :type adapter: str
    :ivar host: The host.
    :type host: str
    :ivar port: The tcp port.
    :type port: int
    """

    TCP = ('amqp', 'tcp')
    SSL = ('amqps', 'ssl')

    @staticmethod
    def split(s):
        """
        Split the url string.
        :type s: str
        :return: The url parts: (adapter, scheme, host, port, userid, password, path)
        :rtype: tuple
        """
        adapter, scheme, netloc, path = \
            URL.split_url(s)
        userid_password, host_port = \
            URL.split_location(netloc)
        userid, password = \
            URL.split_userid_password(userid_password)
        host, port = \
            URL.split_host_port(host_port, URL._port(scheme))
        return adapter, \
            scheme, \
            host, \
            port, \
            userid, \
            password, \
            path

    @staticmethod
    def split_url(s):
        """
        Split the adapter and url parts.
        :param s: A url.
        :type s: str
        :return: (adapter, network-location, path)
        :rtype: tuple
        """
        # adapter
        part = s.split('://', 1)
        if len(part) > 1:
            adapter, host_port = (part[0], part[1])
        else:
            adapter, host_port = (URL.TCP[0], part[0])
        part = host_port.split('/', 1)
        # path
        if len(part) > 1:
            location, path = (part[0], part[1])
        else:
            location, path = (host_port, None)
        adapter, scheme = URL.split_adapter(adapter)
        return adapter, scheme, location, path

    @staticmethod
    def split_adapter(s):
        """
        Split the adapter into gofer-adapter and the scheme.
        :param s: <adapter>+<scheme>
        :return:
        """
        part = s.split('+', 1)
        if len(part) > 1:
            return part[0], part[1]
        else:
            return None, part[0]

    @staticmethod
    def split_location(s):
        """
        Split network location into (userid_password, host_port)
        :param s: A url component: <user>:<password>@<host>:<port>
        :type s: str
        :return: (userid_password, host_port)
        :rtype: tuple
        """
        part = s.split('@', 1)
        if len(part) > 1:
            return part[0], part[1]
        else:
            return '', part[0]

    @staticmethod
    def split_userid_password(s):
        """
        Split the userid and password into (userid, password).
        :param s: A url component: <userid>:<password>.
        :type s: str
        :return: (userid, password)
        :rtype: tuple
        """
        part = s.split(':', 1)
        if len(part) > 1:
            return part[0], part[1]
        else:
            return None, None

    @staticmethod
    def split_host_port(s, default):
        """
        Split the host and port.
        :param s: A url component: <host>:<port>.
        :type s: str
        :return: (host, port)
        :rtype: tuple
        """
        part = s.split(':')
        if len(part) > 1:
            return part[0], int(part[1])
        else:
            return part[0], default

    @staticmethod
    def _port(adapter):
        """
        Get the port based on the adapter.
        :param adapter: The URL adapter or scheme.
        :type adapter: str
        :return: port
        :rtype: int
        """
        if adapter.lower() in URL.SSL:
            return 5671
        else:
            return 5672

    def __init__(self, url):
        """
        :param url: A url string format:
            <adapter>://<host>:<port>userid:password@<adapter>://<host>:<port>.
        :type url: str
        """
        self._input = url
        self.adapter, \
            self.scheme,\
            self.host, \
            self.port, \
            self.userid, \
            self.password,\
            self.path = self.split(url)

    def simple(self):
        """
        Get the *simple* string representation: <host>:<port>
        :return: "<host>:<port>"
        :rtype: str
        """
        return '%s:%d' % (self.host, self.port)

    def is_ssl(self):
        return self.scheme.lower() in self.SSL

    def __hash__(self):
        return hash(self.simple())

    def __eq__(self, other):
        return self.simple() == other.simple()

    def __str__(self):
        return self._input.split('+')[-1]

