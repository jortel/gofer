from gofer.decorators import *
from gofer.agent.plugin import Plugin

from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)


class TestAction:

    @action(hours=36)
    def hello(self):
        plugin = Plugin.find(__name__)
        log.info('Hello:\n%s', plugin.cfg)


class TestAdmin:

    @remote
    def echo(self, thing):
        return thing


class Duck(object):

    @remote
    def quack(self, words):
        return words

    @remote
    def fly(self):
        return 'Headed south for the winter.  Bye.'


@remote
def echo(something):
    return something

