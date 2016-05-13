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

import imp
import inspect
import new

from logging import getLogger
from sys import stdin, stdout, exc_info
from traceback import format_exception

from gofer import utf8
from gofer.agent import rmi
from gofer.agent.logutil import LogHandler
from gofer.rmi.mode import protocol


log = getLogger(__name__)


class TargetNotFound(Exception):

    FORMAT = 'Target "%s" not found: %s'

    def __init__(self, name, exception):
        details = TargetNotFound.FORMAT % (name, utf8(exception))
        Exception.__init__(self, details)


class MethodNotFound(Exception):

    FORMAT = 'Method "%s" not found'

    def __init__(self, name):
        details = MethodNotFound.FORMAT % name
        Exception.__init__(self, details)


class Progress(rmi.Progress):

    def __init__(self):
        super(Progress, self).__init__(None)

    def report(self):
        payload = protocol.Progress.Payload(
            total=self.total,
            completed=self.completed,
            details=self.details)
        reply = protocol.Progress(payload.__dict__)
        reply.send(stdout)


class Raised(protocol.Raised):

    @staticmethod
    def current():
        info = exc_info()
        inst = info[1]
        target = inst.__class__
        description = '\n'.join(format_exception(*info))
        mod = inspect.getmodule(target)
        if mod:
            mod = mod.__name__
        args = None
        if issubclass(target, Exception):
            args = inst.args
        state = dict(inst.__dict__)
        state['trace'] = description
        return Raised.Payload(
            description=description,
            mod=mod,
            target=target.__name__,
            state=state,
            args=args)

    def __init__(self):
        payload = self.current()
        super(Raised, self).__init__(payload.__dict__)


class Request(protocol.Request):

    def get_module(self):
        if '.' in self.mod:
            return __import__(self.mod, fromlist=[self.target])
        else:
            return imp.load_source(self.mod, self.path)

    def get_target(self):
        try:
            mod = self.get_module()
            T = getattr(mod, self.target)
            if inspect.isclass(T):
                if issubclass(T, object):
                    inst = T.__new__(T)
                else:
                    inst = new.instance(T)
                inst.__dict__.update(self.state)
            else:
                inst = mod
            return inst
        except AttributeError, e:
            raise TargetNotFound(self.target, e)

    def get_method(self, inst):
        try:
            return getattr(inst, self.method)
        except AttributeError:
            raise MethodNotFound(self.method)

    def __call__(self):
        """
        Execute the RMI request.
        """
        try:
            target = self.get_target()
            method = self.get_method(target)
            args, kwargs = self.passed
            result = method(*args, **kwargs)
            reply = protocol.Result(result)
            reply.send(stdout)
        except Exception:
            log.exception('call failed')
            reply = Raised()
            reply.send(stdout)


def main():
    sn = ''
    LogHandler.install()
    progress = Progress()
    cancelled = rmi.Cancelled(sn)
    context = rmi.Context(sn, progress, cancelled)
    rmi.Context.set(context)
    request = Request.read(stdin)
    request()


if __name__ == '__main__':  # pragma: no cover
    main()
