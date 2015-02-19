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

import os
import errno

from Queue import Queue
from threading import Thread

from unittest import TestCase

from mock import Mock, patch
from tempfile import mktemp

from gofer.common import Singleton, ThreadSingleton, Options
from gofer.common import synchronized, conditional, mkdir, nvl, valid_path


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


class ThingT(object):

    __metaclass__ = ThreadSingleton

    def __init__(self, n1, n2, a=0, b=0):
        self.__mutex = Mock()
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b


class ThingT2(object):

    __metaclass__ = ThreadSingleton

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


class TestMkdir(TestCase):

    @patch('os.makedirs')
    def test_make(self, mkdirs):
        path = '/tmp/dir'
        mkdir(path)
        mkdirs.assert_called_once_with(path)

    @patch('os.makedirs')
    def test_exists(self, mkdirs):
        path = '/tmp/dir'
        exception = OSError()
        exception.errno = errno.EEXIST
        mkdirs.side_effect = exception
        mkdir(path)

    @patch('os.makedirs')
    def test_failed(self, mkdirs):
        path = '/tmp/dir'
        mkdirs.side_effect = OSError()
        self.assertRaises(OSError, mkdir, path)


class TestNVL(TestCase):

    def test_call(self):
        self.assertEqual(nvl(None, 3), 3)
        self.assertEqual(nvl(1, 2), 1)


class TestSingleton(TestCase):

    def test_call(self):
        args = (1, 2)
        kwargs = {'a': 1, 'b': 2}
        Singleton._inst.clear()

        try:

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
            Singleton._inst.clear()

    def test_key(self):
        args = [
            'A',
            1,
            1.0,
            True,
            Thing
        ]
        keywords = {
            'string': '',
            'int': 1,
            'float': 1.0,
            'bool': True,
            'thing': Thing,
        }

        # test
        key = Singleton.key(args, keywords)

        # validation
        self.assertEqual(
            key,
            "['A', 1, 1.0, True, ('bool', True), ('float', 1.0), ('int', 1), ('string', '')]")


class TestThreadSingleton(TestCase):

    def test_call(self):
        args = (1, 2)
        kwargs = {'a': 1, 'b': 2}
        ThreadSingleton.all().clear()

        try:
            # 1st
            thing = ThingT(*args, **kwargs)
            self.assertTrue(isinstance(thing, ThingT))
            self.assertEqual(thing.n1, args[0])
            self.assertEqual(thing.n2, args[1])
            self.assertEqual(thing.a, kwargs['a'])
            self.assertEqual(thing.b, kwargs['b'])
            # same
            thing2 = ThingT(*args, **kwargs)
            self.assertEqual(id(thing), id(thing2))
            # different arguments
            thing2 = ThingT(3, 4, a=3, b=4)
            self.assertNotEqual(id(thing), id(thing2))
            # different class
            thing2 = ThingT2(*args, **kwargs)
            self.assertNotEqual(id(thing), id(thing2))
        finally:
            ThreadSingleton.all().clear()

    def test_call_different_thread(self):
        args = (1, 2)
        kwargs = {'a': 1, 'b': 2}
        ThreadSingleton.all().clear()

        try:
            thing = ThingT(*args, **kwargs)
            queue = Queue()

            def test():
                thing2 = ThingT(*args, **kwargs)
                queue.put(id(thing2))

            thread = Thread(target=test)
            thread.start()
            thread.join()

            self.assertNotEqual(id(thing), queue.get())
        finally:
            ThreadSingleton.all().clear()

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


class TestValidPath(TestCase):

    def setUp(self):
        self.path = mktemp()

    def tearDown(self):
        if os.path.exists(self.path):
            os.chmod(self.path, 0x666)
            os.unlink(self.path)

    def test_valid(self):
        with open(self.path, 'a'):
            try:
                valid_path(self.path)
            except ValueError:
                self.fail('Value error not expected')

    def test_not_found(self):
        self.assertRaises(ValueError, valid_path, self.path)

    def test_perms(self):
        fp = open(self.path, 'a')
        fp.close()
        os.chmod(self.path, 0x00)
        self.assertRaises(ValueError, valid_path, self.path)
