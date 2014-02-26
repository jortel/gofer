# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gofer.messaging.model import getuuid


class Endpoint(object):
    """
    Base class for an AMQP endpoint.
    :ivar url: The broker URL.
    :type url: str
    :ivar uuid: The unique endpoint id.
    :type uuid: str
    :ivar authenticator: A message authenticator.
    :type authenticator: gofer.messaging.auth.Authenticator
    """

    def __init__(self, uuid=None, url=None):
        """
        :param url: The broker url <transport>://<user>/<pass>@<host>:<port>.
        :type url: str
        :param uuid: The endpoint uuid.
        :type uuid: str
        """
        self.url = url
        self.uuid = uuid or getuuid()
        self.authenticator = None