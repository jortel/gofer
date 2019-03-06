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
      - ttl
          (int) Request TTL (time-to-live).
      - wait
          (int) Seconds to wait for a synchronous reply (default:90).
      - authenticator
          (Authenticator) A message authenticator.
      - progress
          (callable) A progress callback.
      - exchange
          (str) An optional AMQP exchange used for synchronous replies.
      - reply
          (str) An AMQP reply address.
      - trigger
          (int) The trigger type (0=auto|1=manual).
      - data
          (object) User defined data that is round tripped.
          Used for asynchronous reply correlation and cancel criteria.

    :ivar __id: The peer ID.
    :type __id: str
    :ivar __url: The peer URL.
    :type __url: str
    :ivar __options: Container options.
    :type __options: Options
    """

    def __init__(self, url, address, **options):
        """
        :param url: The agent URL.
        :type url: str
        :param address: The AMQP address to the agent.
        :type address: str
        :param options: keyword options.  See documentation.
        :type options: dict
        """
        self.__url = url
        self.__address = address
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
        return builder(name, self.__url, self.__address, self.__options)
        
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
        return '{} options: {}'.format(
            str(self.__address),
            str(self.__options)
        )
    
    def __repr__(self):
        return str(self)
