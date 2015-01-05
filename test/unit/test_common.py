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

from mock import Mock

from gofer.common import Singleton, Options, synchronized, conditional, nvl


class Thing(object):

    __metaclass__ = Singleton

    def __init__(self, n1, n2, a=0, b=0):
        self.__mutex = Mock()
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b


class Thing2(object):

    __metaclass__ = Singleton

    def __init__(self, n1, n2, a=0, b=0):
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b


class Thing3(object):

    def __init__(self, mutex=None, condition=None):
        self.__mutex = mutex
        self.__condition = condition

    @synchronized
    def foo(self, n, a=0):
        return n, a

    @conditional
    def bar(self, n, a=0):
        return n, a


class TestNVL(TestCase):

    def test_call(self):
        self.assertEqual(nvl(None, 3), 3)
        self.assertEqual(nvl(1, 2), 1)


class TestSingleton(TestCase):

    def test_reset(self):
        Singleton._Singleton__inst = {'A': 1}

        # test
        Singleton.reset()

        # validation
        self.assertEqual(Singleton._Singleton__inst, {})

    def test_all(self):
        Singleton._Singleton__inst = {'A': 1}

        # test
        _all = Singleton.all()

        # validation
        self.assertEqual(_all, Singleton._Singleton__inst.values())

    def test_call(self):
        args = (1, 2)
        kwargs = {'a': 1, 'b': 2}

        try:
            Singleton.reset()
            # 1st
            thing = Thing(*args, **kwargs)
            self.assertTrue(isinstance(thing, Thing))
            self.assertEqual(thing.n1, args[0])
            self.assertEqual(thing.n2, args[1])
            self.assertEqual(thing.a, kwargs['a'])
            self.assertEqual(thing.b, kwargs['b'])
            # same
            thing2 = Thing(*args, **kwargs)
            self.assertEqual(id(thing), id(thing2))
            # different arguments
            thing2 = Thing(3, 4, a=3, b=4)
            self.assertNotEqual(id(thing), id(thing2))
            # different class
            thing2 = Thing2(*args, **kwargs)
            self.assertNotEqual(id(thing), id(thing2))
        finally:
            Singleton.reset()

    def test_key(self):
        t = [
            'A',
            1,
            1.0,
            True,
            Thing
        ]
        d = {
            'string': '',
            'int': 1,
            'float': 1.0,
            'bool': True,
            'thing': Thing,
        }

        # test
        key = Singleton.key(t, d)

        # validation
        self.assertEqual(
            key,
            "['A', 1, 1.0, True, ('bool', True), ('float', 1.0), ('int', 1), ('string', '')]")


class TestDecorators(TestCase):

    def test_synchronized(self):
        mutex = Mock()
        thing = Thing3(mutex=mutex)

        # test
        ret = thing.foo(1, a=2)

        # validation
        mutex.acquire.assert_called_once_with()
        mutex.release.assert_called_once_with()
        self.assertEqual(ret, (1, 2))

    def test_synchronized_no_mutex(self):
        thing = Thing3(None)
        self.assertRaises(AttributeError, thing.foo, 0)

    def test_condition(self):
        condition = Mock()
        thing = Thing3(condition=condition)

        # test
        ret = thing.bar(1, a=2)

        # validation
        condition.acquire.assert_called_once_with()
        condition.release.assert_called_once_with()
        self.assertEqual(ret, (1, 2))

    def test_conditional_no_condition(self):
        thing = Thing3(None)
        self.assertRaises(AttributeError, thing.bar, 0)


class TestOptions(TestCase):

    def test_init(self):
        # dict
        d = {'A': 1}
        options = Options(d)
        self.assertEqual(d, options.__dict__)
        # options
        d = {'A': 1}
        options = Options(Options(d))
        self.assertEqual(d, options.__dict__)
        # ValueError
        self.assertRaises(ValueError, Options, 1)

    def test_getattr(self):
        options = Options(a=1)
        self.assertEqual(options.a, 1)

    def test_get_item(self):
        options = Options(a=1)
        self.assertEqual(options['a'], 1)

    def test_set_item(self):
        options = Options()
        options['a'] = 1
        self.assertEqual(options['a'], 1)

    def test_iadd_object(self):
        opt1 = Options(a=1)
        opt2 = Options(b=2)
        opt1 += opt2
        self.assertEqual(opt1.__dict__, {'a': 1, 'b': 2})

    def test_iadd_dict(self):
        opt1 = Options(a=1)
        opt2 = dict(b=2)
        opt1 += opt2
        self.assertEqual(opt1.__dict__, {'a': 1, 'b': 2})

    def test_iadd_other(self):
        opt1 = Options(a=1)
        opt2 = None
        try:
            opt1 += opt2
            self.assertTrue(0, msg='ValueError expected')
        except ValueError:
            pass

    def test_len(self):
        options = Options(a=1, b=2)
        self.assertEqual(len(options), 2)

    def test_iter(self):
        options = Options(a=1, b=2)
        _list = list(iter(options))
        self.assertEqual(_list, ['a', 'b'])

    def test_repr(self):
        options = Options(a=1, b=2)
        self.assertEqual(repr(options), repr(options.__dict__))

    def test_str(self):
        options = Options(a=1, b=2)
        self.assertEqual(str(options), str(options.__dict__))
