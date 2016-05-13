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

import re

from logging import getLogger

from gofer.common import json, new


log = getLogger(__file__)


class End(Exception):

    def __init__(self, result=None):
        Exception.__init__(self)
        self.result = result


class ProtocolError(Exception):
    pass


class Message(object):

    PATTERN = re.compile(r'^\{.+\}\n$')

    @classmethod
    def load(cls, message):
        return new(cls, json.loads(message))

    @classmethod
    def read(cls, pipe):
        while True:
            line = pipe.readline()
            if not line:
                raise End()
            if not Message.PATTERN.match(line):
                continue
            log.debug('%s received: %s', cls.__name__, line)
            return cls.load(line)

    def send(self, pipe):
        name = self.__class__.__name__
        message = json.dumps(self.__dict__)
        pipe.write(message)
        log.debug('%s sent: %s', name, message)
        pipe.write('\n')
        pipe.flush()


class Request(Message):

    def __init__(self, path, mod, target, state, method, passed):
        self.path = path
        self.mod = mod
        self.target = target
        self.state = state
        self.method = method
        self.passed = passed


class Reply(Message):

    PATTERN = re.compile(r'^\{.+\}\n$')

    registry = {}

    def __init__(self, code, payload):
        self.code = code
        self.payload = payload

    @staticmethod
    def register(code, target):
        Reply.registry[code] = target

    def __call__(self):
        try:
            T = Reply.registry[self.code]
            target = T(self.payload)
            target()
        except KeyError:
            log.debug('Reply: [%s] discarded', self.code)


class Progress(Reply):

    CODE = 'PROGRESS'

    class Payload(object):
        def __init__(self, total, completed, details):
            self.total = total
            self.completed = completed
            self.details = details

    def __init__(self, payload):
        super(Progress, self).__init__(self.CODE, payload)


class Result(Reply):

    CODE = 'RESULT'

    def __init__(self, payload):
        super(Result, self).__init__(self.CODE, payload)


class Error(Reply):

    CODE = 'ERROR'

    def __init__(self, payload):
        super(Error, self).__init__(self.CODE, payload)


class Raised(Reply):

    CODE = 'RAISED'

    class Payload(object):
        def __init__(self, description, mod, target, state, args):
            self.description = description
            self.target = target
            self.mod = mod
            self.target = target
            self.state = state
            self.args = args

    def __init__(self, payload):
        super(Raised, self).__init__(self.CODE, payload)
