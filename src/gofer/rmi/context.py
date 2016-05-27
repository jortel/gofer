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
from logging import getLogger

from gofer.common import Local
from gofer.rmi.tracker import Tracker
from gofer.messaging import Producer


log = getLogger(__name__)


class Context(object):
    """
    Remote method invocation context.
    Provides mode context to method implementations.
    :ivar sn: The current request serial number.
    :type sn: str
    :ivar progress: Provides progress reporting.
    :type progress: Progress
    :ivar cancelled: Provides cancellation status.
    :type cancelled: Cancelled
    """

    _current = Local()

    @staticmethod
    def set(context=None):
        """
        Set the current context.
        :param context: The current context.
        :type context: Context
        """
        Context._current.inst = context

    @staticmethod
    def current():
        """
        Get the current context.
        :return: The current context
        :rtype: Context
        """
        try:
            return Context._current.inst
        except AttributeError:
            return None

    def __init__(self, sn, progress, cancelled):
        """
        :param sn: The current request serial number.
        :type  sn: str
        :param progress: Provides progress reporting.
        :type  progress: Progress
        :param cancelled: Provides cancellation status.
        :type  cancelled: Cancelled
        """
        self.sn = sn
        self.progress = progress
        self.cancelled = cancelled


class Progress(object):
    """
    Provides support for progress reporting.
    :ivar request: The current request.
    :type request: gofer.messaging.Document
    :ivar producer: An open AMQP producer.
    :type producer: gofer.messaging.Producer
    :ivar total: The total work units.
    :type total: int
    :ivar completed: The completed work units.
    :type completed: int
    :ivar details: The reported details.
    :type details: object
    """

    def __init__(self, request, producer):
        """
        :param request: The current request.
        :type request: gofer.messaging.Document
        :param producer: An open AMQP producer.
        :type producer: gofer.messaging.Producer
        """
        self.request = request
        self.producer = producer
        self.total = 0
        self.completed = 0
        self.details = {}

    def report(self):
        """
        Send the progress report.
        """
        sn = self.request.sn
        data = self.request.data
        address = self.request.replyto
        if not address:
            return
        try:
            self.producer.send(
                address,
                sn=sn,
                data=data,
                status='progress',
                total=self.total,
                completed=self.completed,
                details=self.details)
        except Exception:
            log.exception('Send: progress, failed')


class Cancelled(object):
    """
    A callable added to the Context and used
    by plugin methods to check for cancellation.
    :ivar sn: The current request serial number.
    :type sn: str
    :ivar tracker: The cancellation tracker.
    :type tracker: Tracker
    """

    def __init__(self, sn):
        """
        :param sn: The current request serial number.
        :type sn: str
        """
        self.sn = sn
        self.tracker = Tracker()

    def __call__(self):
        return self.tracker.cancelled(self.sn)

    def __del__(self):
        try:
            self.tracker.remove(self.sn)
        except KeyError:
            # already cleaned up
            pass
