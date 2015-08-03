
import os
import sys
import inspect
import traceback as tb

from gofer.rmi.shell import Shell
from gofer.messaging import Document


def exception():
    try:
        return raised()
    except TypeError:
        return raised()


def raised():
    info = sys.exc_info()
    inst = info[1]
    xclass = inst.__class__
    exval = '\n'.join(tb.format_exception(*info))
    mod = inspect.getmodule(xclass)
    if mod:
        mod = mod.__name__
    args = None
    if issubclass(xclass, Exception):
        args = inst.args
    state = dict(inst.__dict__)
    state['trace'] = exval
    inst = Document(
        exval=exval,
        xmodule=mod,
        xclass=xclass.__name__,
        xstate=state,
        xargs=args)
    inst.dump()  # validate json
    return inst


def write(fd, s):
    os.write(fd, '%.10d' % len(s))
    os.write(fd, retval)


def read(fd):
    length = int(os.read(fd, 10))
    return os.read(fd, length)


class Method(object):

    def __init__(self, name, thing):
        self.name = name
        self.thing = thing
        self.pipe = os.pipe()

    def __call__(self, *args, **options):
        shell = Shell()
        call = Document(
            thing=self.thing,
            name=self.name,
            pipe=self.pipe,
            args=args,
            options=options)
        _, retval = shell.run(sys.executable, '-m', __name__, call.dump())
        if _ == 0:
            output = Document()
            output.load(read(self.pipe[0]))
            return output.exception or output.retval
        else:
            return retval


class Thing(object):

    def __init__(self, thing, *args, **options):
        self.thing = thing
        self.args = args
        self.options = options

    def __getattr__(self, name):
        thing = Document(
            path=self.thing.__name__,
            args=self.args,
            options=self.options)
        return Method(name, thing)


if __name__ == '__main__':
    call = Document()
    call.load(sys.argv[1])
    call.thing = Document(call.thing)
    path = call.thing.path.rsplit('.', 1)
    if len(path) == 1:
        thing = __import__(path[0])
    else:
        thing = __import__(path[0], [path[1]])
    if inspect.isclass(thing):
        inst = thing(*call.thing.args, **call.thing.options)
    else:
        inst = thing
    method = getattr(inst, call.name)
    result = Document()
    try:
        result.retval = method(*call.args, **call.options)
    except Exception, mx:
        result.exception = exception()
    retval = result.dump()
    write(call.pipe[1], retval)
    os.close(call.pipe[1])
