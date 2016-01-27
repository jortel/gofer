import json


class Model(object):

    @staticmethod
    def load(s):
        pass

    def dump(self):
        return json.dumps(self.__dict__)


class Security(Model):

    def __init__(self, message, signature):
        self.message = message
        self.signature = signature


class Envelope(Model):

    def __init__(self):
        self.sn = None
        self.version = None
        self.routing = tuple()
        self.timestamp = None
        self.data = None
        self.request = None
        self.result = None
        self.status = None


class Request(Envelope):

    def __init__(self, classname, method, cntr, args, kws):
        super(Request, self).__init__()
        self.classname = classname
        self.method = method
        self.cntr = cntr
        self.args = args
        self.kws = kws


class Status(Envelope):

    def __init__(self, status):
        super(Status, self).__init__()
        self.status = status


class Progress(Envelope):

    def __init__(self, total, completed, details):
        super(Progress, self).__init__()
        self.total = total
        self.completed = completed
        self.details = details


class Result(Envelope):

    def __init__(self, retval):
        super(Result, self).__init__()
        self.retval = retval


class Raised(Envelope):

    def __init__(self, exval, xmodule, xclass, xstate, xargs):
        super(Raised, self).__init__()
        self.exval = exval
        self.xmodule = xmodule
        self.xclass = xclass
        self.xstate = xstate
        self.xargs = xargs
