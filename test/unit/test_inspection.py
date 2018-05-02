# Copyright (c) 2018 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import inspect

from unittest import TestCase

from gofer import inspection


THIS_SHOULD_BE_IGNORED = 'XX'


def add(a, b):
    return a + b


class Person(object):
    name = ''
    age = 0

    @staticmethod
    def kill(pid):
        pass

    def __init__(self, parent=None):
        self.parent = parent

    def walk(self, direction, speed=10, other=1):
        pass

    def run(self):
        pass


class TestInspection(TestCase):

    def test_methods(self):
        methods = inspection.methods(Person)
        self.assertEqual(4, len(methods))
        self.assertEqual(
            [
                '__init__',
                'kill',
                'run',
                'walk'
            ],
            sorted([m[0] for m in methods])
        )
        for m in methods:
            self.assertTrue(inspect.isfunction(m[1]))

    def test_method(self):
        name = 'walk'
        function_ = inspection.method(Person, name)
        self.assertTrue(inspect.isfunction(function_))

    def test_signature(self):
        function_ = inspection.method(Person, 'walk')
        signature = inspection.signature(function_)
        self.assertEqual('(self, direction, speed=10, other=1)', signature)

    def test_classes(self):
        classes = inspection.classes(inspection.module(add))
        self.assertEqual(
            sorted([
                'Person',
                'TestCase',
                'TestInspection'
             ]),
            sorted([c[0] for c in classes])
        )

    def test_is_module(self):
        self.assertTrue(inspection.is_module(inspect))

    def test_is_class(self):
        self.assertTrue(inspection.is_class(Person))

    def test_mro(self):
        order = inspection.mro(Person)
        self.assertEqual(order, (Person, object))
