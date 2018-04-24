

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

from gofer import inspection
from gofer.agent.action import Action
from gofer.agent.reporting import indent, loaded
from gofer.collation import Module, Class, Method, Function


HELP = """\
Plugins:

  <plugin> animals
    Classes:
      <class> Dog
        Methods:
          fn(name, age)
          fn1(self, words)
          fn2(self, words, *others)
          fn3(self, words, *others, **keywords)
    Functions:
      bar1(n)
      bar2(age)
      bar3(month, day, year)

Actions:
  reboot 0:10:00
  report 1 day, 0:00:00\
"""


def bar1(n):
    pass


def bar2(age):
    pass


def bar3(month, day, year):
    pass


class Dog(object):

    @staticmethod
    def fn(name, age):
        pass

    def fn1(self, words):
        pass

    def fn2(self, words, *others):
        pass

    def fn3(self, words, *others, **keywords):
        pass


class Plugin(object):

    def __init__(self, name, enabled, dispatcher):
        self.name = name
        self.enabled = enabled
        self.dispatcher = dispatcher


class TestUtils(TestCase):

    def test_indent(self):
        string = 'My {} has nine lives'
        cat = 'cat'
        actual = indent(string, 4, cat)
        expected = '    ' + string.format(cat)
        self.assertEqual(expected, actual)


class TestReports(TestCase):

    @patch('gofer.agent.decorator.Actions')
    def test_loaded(self, actions):
        catalog = {
            Dog.__name__: Class(
                Dog,
                methods={
                    n: Method(m) for n, m in inspection.methods(Dog)
                }
            ),
            'stuff': Module(
                'stuff',
                functions={
                    bar1.__name__: Function(bar1),
                    bar2.__name__: Function(bar2),
                    bar3.__name__: Function(bar3),
                }
            )
        }
        plugins = [
            Plugin('animals', True, Mock(catalog=catalog)),
            Plugin('fish', False, None),
        ]

        container = Mock()
        container.all.return_value = plugins

        actions.collated.return_value = [
            Action('report', None, hours=24),
            Action('reboot', None, minutes=10)
        ]

        # test
        actual = loaded(container, actions)

        # validation
        expected = HELP % {'plugin': plugins[0].name}
        self.assertEqual(expected, actual)
