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

from gofer.common import utf8


log = getLogger(__file__)


class End(Exception):
    """
    End of child reply processing.
    """

    def __init__(self, result=None):
        """
        :param result: The RMI retval.
        """
        Exception.__init__(self)
        self.result = result


class Call(object):
    """
    An RMI call.
    """

    def __init__(self, method, *args, **kwargs):
        """
        :param method: The method to be invoked.
        :type method: callable
        :param args: Passed arguments.
        :type args: tuple
        :param kwargs: Passed keyword arguments.
        :type kwargs: dict
        """
        self.method = method
        self.args = args
        self.kwargs = kwargs


class Message(object):
    """
    A json encoded message.
    """

    @classmethod
    def read(cls, pipe):
        """
        Read the next message from the pipe.
        :param pipe: A message pipe.
        :type  pipe: gofer.mp.Reader
        :return: The hydrated message.
        :rtype: Message
        """
        try:
            pipe.poll()
            message = pipe.get()
            if not message:
                raise EOFError()
            log.debug('Received: %s', message)
            return message
        except EOFError:
            raise End()

    def send(self, pipe):
        """
        Put json encoded (self) into the pipe.
        :param pipe: A message pipe.
        :type  pipe: gofer.mp.Writer
        """
        pipe.put(self)
        log.debug('Sent: %s', self)

    def __str__(self):
        return ':'.join((self.__class__.__name__, utf8(self.__dict__)))


class Reply(Message):
    """
    A child reply message.
    This is an event relayed by the child process that needs
    to be propagated to the parent.
    :cvar registry: Message objects mapped to codes.
    :type registry: dict
    :ivar code: Message code.
    :type code: str
    :ivar payload: Message payload.
    :type payload: object
    """

    registry = {}

    def __init__(self, code, payload):
        """
        :param code: Message code.
        :type code: str
        :param payload: Message payload.
        :type payload: object
        """
        self.code = code
        self.payload = payload

    @staticmethod
    def register(code, target):
        """
        Register a reply class to its code.
        When a message with the *code* is received, the object is
        hydrated and called.
        :param code: A reply code.
        :type code: str
        :param target: A reply class.
        :type target: Reply
        """
        Reply.registry[code] = target

    def __call__(self):
        """
        Find the registered message class by code and create
        an instance it with the payload.  Then, the message is
        invoked to propagate event on the parent.
        """
        try:
            T = Reply.registry[self.code]
            target = T(self.payload)
            target()
        except KeyError:
            log.debug('Reply: [%s] discarded', self.code)


class ProgressPayload(object):
    """
    The message payload.
    :ivar total: The total work units.
    :type total: int
    :ivar completed: The completed work units.
    :type completed: int
    :ivar details: The reported details.
    :type details: object
    """
    def __init__(self, total, completed, details):
        """
        :ivar total: The total work units.
        :type total: int
        :ivar completed: The completed work units.
        :type completed: int
        :ivar details: The reported details.
        :type details: object
        """
        self.total = total
        self.completed = completed
        self.details = details

    def __repr__(self):
        return str(self)

    def __str__(self):
        return utf8(self.__dict__)


class Progress(Reply):
    """
    A PROGRESS reporting event.
    """

    CODE = 'PROGRESS'

    def __init__(self, payload):
        """
        :param payload: The reported progress.
        :type payload: ProgressPayload
        """
        super(Progress, self).__init__(self.CODE, payload)


class Result(Reply):
    """
    A RESULT reporting event.
    """

    CODE = 'RESULT'

    def __init__(self, payload):
        """
        :param payload: The reported result.
        :type payload: object
        """
        super(Result, self).__init__(self.CODE, payload)


class Error(Reply):
    """
    An ERROR reporting event.
    """

    CODE = 'ERROR'

    def __init__(self, payload):
        """
        :param payload: The reported result.
        :type payload: object:
        """
        super(Error, self).__init__(self.CODE, payload)


class Raised(Reply):
    """
    A RAISED (exception) reporting event.
    """

    CODE = 'RAISED'

    def __init__(self, payload):
        """
        :param payload: The reported result.
        :type payload: object
        """
        super(Raised, self).__init__(self.CODE, payload)
