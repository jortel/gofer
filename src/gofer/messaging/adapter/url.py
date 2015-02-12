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

AMQP = {
    'tcp':  5672,
    'amqp': 5672,
}

AMQPS = {
    'ssl':   5671,
    'amqps': 5671,
}

PORT = {}
PORT.update(AMQP)
PORT.update(AMQPS)


class Part(object):
    """
    Basic URL component.
    :ivar parts: component parts.
    :type parts: list
    """

    def __init__(self, fragment, delimiter):
        """
        :param fragment: A URL fragment.
        :type fragment: str
        :param delimiter: A delimiter used to split the fragment.
        :type delimiter: str
        """
        if fragment:
            self.parts = fragment.split(delimiter, 1)
        else:
            self.parts = []


class URL(Part):
    """
    Represents a broker URL.
    Format: <adapter>+<scheme>://<user>:<password>@<host>:<port></>.
    :ivar adapter: The messaging adapter.
    :type adapter: str
    :ivar scheme: The URL scheme.
    :type scheme: str
    :ivar host: The host name or IP.
    :type host: str
    :ivar port: The tcp port.
    :type port: int
    :ivar userid: A user name (auth).
    :type userid: str
    :ivar password: A user password (auth).
    :type password: str
    :ivar path: The path component.
    :type path: str
    """

    def __init__(self, url):
        """
        :param url: A url string format:
            <adapter>+<scheme>://<userid>:<password>@<host>:<port>/<path>
        :type url: str
        """
        super(URL, self).__init__(url, '://')
        if len(self.parts) == 0:
            self.parts = [url]
        if len(self.parts) > 1:
            scheme = Scheme(self.parts[0])
            path = Path(self.parts[1])
        else:
            scheme = Scheme('')
            path = Path(self.parts[0])
        location = path.location
        auth = location.auth
        host = location.host
        self._input = url
        self.adapter = scheme.adapter
        self.scheme = scheme.name
        self.host = host.name
        self.port = host.port or PORT[scheme.name]
        self.userid = auth.userid
        self.password = auth.password
        self.path = path.path

    @property
    def canonical(self):
        """
        A *canonical* string representation.
        :return: "<scheme>://<userid>:<password>@<host>:<port>/path"
        :rtype: str
        """
        url = '%s://' % self.scheme
        if self.userid:
            url += '%(u)s:%(p)s@' % {'u': self.userid, 'p': self.password}
        url += self.host
        if self.port not in PORT.values():
            url += ':%d' % self.port
        return url

    def is_ssl(self):
        return self.scheme in AMQPS

    def __hash__(self):
        return hash(self.canonical)

    def __eq__(self, other):
        return self.canonical == other.canonical

    def __str__(self):
        return self.canonical


class Scheme(Part):
    """
    The *scheme* component of a URL.
    ...<adapter>+<scheme>...
    """

    @staticmethod
    def validated(name):
        supported = PORT.keys()
        if name not in supported:
            raise ValueError('must be: ' % supported)
        return name.lower()

    def __init__(self, fragment):
        super(Scheme, self).__init__(fragment, '+')

    @property
    def adapter(self):
        if len(self.parts) > 1:
            return self.parts[0]
        else:
            return None

    @property
    def name(self):
        if len(self.parts) > 1:
            name = self.parts[1]
            return self.validated(name)
        if len(self.parts):
            name = self.parts[0]
            return self.validated(name)
        return 'amqp'


class Auth(Part):
    """
    The *authentication* component of a URL.
    ...<user>:<password>...
    """

    def __init__(self, fragment):
        super(Auth, self).__init__(fragment, ':')

    @property
    def userid(self):
        if len(self.parts):
            return self.parts[0]
        else:
            return None

    @property
    def password(self):
        if len(self.parts) > 1:
            return self.parts[1]
        else:
            return None


class Location(Part):
    """
    The *network location* component of the URL.
    ...<user>:<password>@<host>:<port>...
    """

    def __init__(self, fragment):
        super(Location, self).__init__(fragment, '@')

    @property
    def auth(self):
        if len(self.parts) > 1:
            fragment = self.parts[0]
        else:
            fragment = ''
        return Auth(fragment)

    @property
    def host(self):
        if len(self.parts) > 1:
            return Host(self.parts[1])
        if len(self.parts):
            return Host(self.parts[0])
        return Host('')


class Path(Part):
    """
    The *path* part of the URL.
    .../<path>
    """

    def __init__(self, fragment):
        super(Path, self).__init__(fragment, '/')

    @property
    def location(self):
        if len(self.parts):
            return Location(self.parts[0])
        else:
            return Location('')

    @property
    def path(self):
        if len(self.parts) > 1:
            return self.parts[1]
        else:
            return None


class Host(Part):
    """
    The *host/port* component of the URL.
    ...<host>:<port>...
    """

    def __init__(self, fragment):
        super(Host, self).__init__(fragment, ':')

    @property
    def name(self):
        if len(self.parts):
            return self.parts[0]
        else:
            return None

    @property
    def port(self):
        if len(self.parts) > 1:
            return int(self.parts[1])
        else:
            return None
