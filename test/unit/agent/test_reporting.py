

# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import Mock, patch

from gofer.agent.reporting import indent, signature, loaded


HELP = """\
Plugins:

  <plugin> animals
    Classes:
      <class> dog
        methods:
          fn1(words)
          fn2(words, *others)
    Functions:
      bar(n)
      bar1(age)

Actions:
  report {'hours': 24}
  reboot {'minutes': 10}\
"""


def remote(fn):
    fn.gofer = {}
    return fn


class Dog(object):

    @staticmethod
    @remote
    def fn(name, age):
        pass

    @remote
    def fn1(self, words):
        pass

    @remote
    def fn2(self, words, *others):
        pass

    def fn3(self, words, *others, **keywords):
        pass


class Plugin(object):

    def __init__(self, name, enabled, dispatcher):
        self.name = name
        self.enabled = enabled
        self.dispatcher = dispatcher


class Action(object):

    def __init__(self, name, interval):
        self._name = name
        self.interval = interval

    def name(self):
        return self._name


class Module(object):

    @remote
    def bar(self, n):
        pass

    @remote
    def bar1(self, age):
        pass

    def bar2(self):
        pass


class TestUtils(TestCase):

    def test_indent(self):
        fmt = 'My %s has nine lives'
        cat = 'cat'
        s = indent(fmt, 4, cat)
        self.assertEqual(s, '    ' + fmt % cat)

    def test_signature(self):
        # function
        fn = Dog.fn
        self.assertEqual(signature(fn.__name__, fn), 'fn(name, age)')
        # method
        fn = Dog.fn1
        self.assertEqual(signature(fn.__name__, fn), 'fn1(words)')
        # method with varargs
        fn = Dog.fn2
        self.assertEqual(signature(fn.__name__, fn), 'fn2(words, *others)')
        # method with varargs and keywords
        fn = Dog.fn3
        self.assertEqual(signature(fn.__name__, fn), 'fn3(words, *others, **keywords)')


class TestReports(TestCase):

    @patch('gofer.agent.reporting.inspect.isfunction')
    @patch('gofer.agent.reporting.inspect.ismodule')
    def test_help(self, is_mod, is_fn):
        is_mod.side_effect = lambda thing: thing == Module
        is_fn.return_value = True
        container = Mock()
        actions = Mock()
        actions.collated.return_value = [
            Action('report', dict(hours=24)),
            Action('reboot', dict(minutes=10)),
        ]
        dispatcher = Mock(catalog={
            'dog': Dog,
            'mod': Module,
        })
        plugins = [
            Plugin('animals', True, dispatcher),
            Plugin('fish', False, None),
        ]
        container.all.return_value = plugins

        # test
        s = loaded(container, actions)

        # validation
        self.assertEqual(s, HELP % {'plugin': plugins[0].name})
