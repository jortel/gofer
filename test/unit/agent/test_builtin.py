
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

from gofer.agent.builtin import indent, signature


def remote(fn):
    fn.gofer = {}
    return fn


with patch('gofer.agent.builtin.remote', remote):
    from gofer.agent.builtin import Admin


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


HELP = """\
Plugins:

  <plugin> animals
    Classes:
      <class> admin
        methods:
          cancel(sn, criteria)
          hello()
          help()
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


class TestAdmin(TestCase):

    @patch('gofer.agent.builtin.Tracker')
    def test_cancel_sn(self, tracker):
        sn = '1234'
        admin = Admin()
        canceled = admin.cancel(sn=sn)
        tracker.return_value.cancel.assert_called_once_with(sn)
        self.assertEqual(canceled, [tracker.return_value.cancel.return_value])

    @patch('gofer.agent.builtin.Builder')
    @patch('gofer.agent.builtin.Tracker')
    def test_cancel_criteria(self, tracker, builder):
        sn = '1234'
        name = 'joe'
        criteria = {'eq': name}
        tracker.return_value.find.return_value = [sn]

        # test
        admin = Admin()
        canceled = admin.cancel(criteria=criteria)

        # validation
        builder.return_value.build.assert_called_once_with(criteria)
        tracker.return_value.cancel.assert_called_once_with(sn)
        self.assertEqual(canceled, [tracker.return_value.cancel.return_value])

    def test_hello(self):
        admin = Admin()
        self.assertEqual(admin.hello(), 'Hello, I am gofer agent')

    @patch('gofer.agent.builtin.inspect.isfunction')
    @patch('gofer.agent.builtin.inspect.ismodule')
    @patch('gofer.agent.builtin.Actions')
    @patch('gofer.agent.builtin.Plugin')
    def test_help(self, plugin, actions, is_mod, is_fn):
        is_mod.side_effect = lambda thing: thing == Module
        is_fn.return_value = True
        actions.return_value.collated.return_value = [
            Action('report', dict(hours=24)),
            Action('reboot', dict(minutes=10)),
        ]
        dispatcher = Mock(catalog={
            'admin': Admin,
            'dog': Dog,
            'mod': Module,
        })
        plugins = [
            Plugin('animals', True, dispatcher),
            Plugin('fish', False, None),
        ]
        plugin.all.return_value = plugins

        # test
        admin = Admin()
        s = admin.help()

        # validation
        self.assertEqual(s, HELP % {'plugin': plugins[0].name})
