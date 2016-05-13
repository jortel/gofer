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

import inspect

from logging import getLogger, LogRecord
from subprocess import Popen, PIPE
from sys import executable as python
from time import sleep
from threading import Thread

from gofer.common import new
from gofer.agent.rmi import Context
from gofer.agent.logutil import LogHandler
from gofer.rmi.mode import protocol, child


log = getLogger(__file__)


class Monitor(Thread):

    NAME = 'mode-monitor'

    def __init__(self, context, child):
        super(Monitor, self).__init__(name=Monitor.NAME)
        self.context = context
        self.child = child
        self.setDaemon(True)
        self.poll = True

    def stop(self):
        self.poll = False
        self.join()

    def run(self):
        while self.poll:
            if self.context.cancelled():
                self.child.terminate()
                break
            else:
                sleep(0.10)


class Result(protocol.Result):

    def __call__(self):
        raise protocol.End(self.payload)


class Progress(protocol.Progress):

    def __call__(self):
        payload = Progress.Payload(**self.payload)
        context = Context.current()
        context.progress.__dict__.update(payload.__dict__)
        context.progress.report()


class Error(protocol.Error):

    def __call__(self):
        raise Exception(self.payload)


class Raised(protocol.Raised):

    def __call__(self):
        payload = Raised.Payload(**self.payload)
        try:
            mod = __import__(payload.mod, {}, {}, fromlist=[payload.target])
            T = getattr(mod, payload.target)
            try:
                inst = new(T, payload.state)
            except:
                inst = Exception.__new__(T)
            if isinstance(inst, Exception):
                inst.args = tuple(payload.args)
        except:
            inst = Exception(payload.description)
        raise inst


class Request(protocol.Request):

    REPLY_PATTERN = protocol.Reply.PATTERN

    @staticmethod
    def build(inst, method, passed):
        mod = inspect.getmodule(inst)
        return Request(
            path=mod.__file__,
            mod=mod.__name__,
            target=inst.__class__.__name__,
            state=inst.__dict__,
            method=method.__name__,
            passed=passed)

    def __call__(self):
        p = Popen([python, child.__file__], stdin=PIPE, stdout=PIPE)
        monitor = Monitor(Context.current(), p)
        try:
            monitor.start()
            self.send(p.stdin)
            return self.read(p.stdout)
        finally:
            monitor.stop()
            p.stdin.close()
            p.stdout.close()
            p.wait()

    def read(self, pipe):
        while True:
            try:
                reply = protocol.Reply.read(pipe)
                reply()
            except protocol.End, end:
                return end.result


protocol.Reply.register(Result.CODE, Result)
protocol.Reply.register(Progress.CODE, Progress)
protocol.Reply.register(Error.CODE, Error)
protocol.Reply.register(Raised.CODE, Raised)

