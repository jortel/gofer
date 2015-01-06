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
Agent base classes.
"""

from logging import getLogger

from gofer.common import Options
from gofer.rmi.stub import Builder


log = getLogger(__name__)

        
class Container(object):
    """
    The stub container
    Options:
      - wait
          (int) Seconds to wait for a synchronous reply (default:90).
      - timeout
          (int) Request timeout TTL (default: 10).
      - window
          (Window) Request valid window.
      - authenticator
          (Authenticator) A message authenticator.
      - progress
          (callable) A progress callback.
      - secret
          (str) A shared secret.
      - user
          (str) A user (name) used for authentication.
      - password
          (str) A password used for authentication.
      - exchange
          (str) An optional AMQP exchange used for synchronous replies.
      - route
          (str) An AMQP route to the agent.  Eg: amq.direct/queue
      - reply
          (str) An AMQP reply route.
      - trigger
          (int) The trigger type (0=auto|1=manual).

    :ivar __id: The peer ID.
    :type __id: str
    :ivar __url: The peer URL.
    :type __url: str
    :ivar __options: Container options.
    :type __options: Options
    """

    def __init__(self, uuid, url, **options):
        """
        :param uuid: The peer ID.
        :type uuid: str
        :param url: The agent URL.
        :type url: str|None
        :param options: keyword options.  See documentation.
        :type options: dict
        """
        self.__id = uuid
        self.__url = url
        self.__route = options.pop('route', uuid)
        self.__options = Options(options)

    def __getattr__(self, name):
        """
        Get a stub by name.
        :param name: The name of a stub class.
        :type name: str
        :return: A stub object.
        :rtype: Stub
        """
        builder = Builder()
        return builder(name, self.__url, self.__route, self.__options)
        
    def __getitem__(self, name):
        """
        Get a stub by name.
        :param name: The name of a stub class.
        :type name: str
        :return: A stub object.
        :rtype: Stub
        """
        return getattr(self, name)

    def __str__(self):
        return '{%s} opt:%s' % (self.__id, str(self.__options))
    
    def __repr__(self):
        return str(self)
