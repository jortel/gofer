from __future__ import print_function


from logging import basicConfig, DEBUG
from time import sleep

from gofer.rmi.context import Context
from gofer.rmi.model.fork import Call


class Cancelled(object):

    def __call__(self):
        return 0


class Progress(object):

    def report(self):
        print(self.__dict__)


class Thing(object):

    def echo(self, n):
        context = Context.current()
        for x in range(n):
            context.progress.details = 'hello {}'.format(x)
            context.progress.report()
            sleep(0.25)
        return n


def main():
    basicConfig(level=DEBUG)
    thing = Thing()
    context = Context('0', Progress(), Cancelled())
    Context.set(context)
    call = Call(thing.echo, 10000)
    print(call())


if __name__ == '__main__':
    main()
