#
# Copyright (c) 2016 Red Hat, Inc.
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

from logging import getLogger

from gofer import utf8
from gofer.rmi.context import Context
from gofer.rmi.model import protocol


log = getLogger(__name__)


class Call(protocol.Call):
    """
    The child-side of the forked call.
    """

    def __call__(self, pipe):
        """
        Perform RMI on the child-side of the forked call
        as follows:
          - Reset the RMI context.
          - Invoke the method
          - Send result: retval, progress, raised exception.
        All output is sent to the parent using the inter-process pipe.
        :param pipe: A message pipe.
        :type  pipe: multiprocessing.Connection
        """
        try:
            context = Context.current()
            context.cancelled = lambda: False
            context.progress = Progress(pipe)
            result = self.method(*self.args, **self.kwargs)
            reply = protocol.Result(result)
            reply.send(pipe)
        except Exception, e:
            log.exception(utf8(e))
            reply = protocol.Raised(e)
            reply.send(pipe)


class Progress(object):
    """
    Provides progress reporting to the parent through the pipe.
    :ivar pipe: A message pipe.
    :type pipe: multiprocessing.Connection
    :ivar total: The total work units.
    :type total: int
    :ivar completed: The completed work units.
    :type completed: int
    :ivar details: The reported details.
    :type details: object
    """

    def __init__(self, pipe):
        """
        :param pipe: A message pipe.
        :type  pipe: multiprocessing.Connection
        """
        self.pipe = pipe
        self.total = 0
        self.completed = 0
        self.details = {}

    def report(self):
        """
        Report progress.
        """
        payload = protocol.ProgressPayload(
            total=self.total,
            completed=self.completed,
            details=self.details)
        reply = protocol.Progress(payload)
        reply.send(self.pipe)
