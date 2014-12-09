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

from time import sleep

from gofer.messaging.model import ModelError


DELAY = 0.0010
MAX_DELAY = 2.0
DELAY_MULTIPLIER = 1.2


def model(fn):
    """
    Model decorator.
    :param fn: Any model function.
    :type fn: function
    :return: The decorator.
    :rtype: function
    """
    def dfn(*args, **keywords):
        try:
            return fn(*args, **keywords)
        except ModelError:
            raise
        except Exception, e:
            raise ModelError(e)
    return dfn


def blocking(fn):
    """
    Blocking read decorator.
    Used by *real* Reader.get() when blocking read not supported.
    :param fn: A Reader.get() function.
    :type fn: function
    :return: blocking read function.
    :rtype: function
    """
    def dfn(reader, timeout=None):
        delay = DELAY
        timer = float(timeout or 0)
        while True:
            message = fn(reader, timer)
            if message:
                return message
            if timer > 0:
                sleep(delay)
                timer -= delay
                if delay < MAX_DELAY:
                    delay *= DELAY_MULTIPLIER
            else:
                break
    return dfn
