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

from six import unichr
from six.moves.queue import Queue
from threading import Thread, Event

from unittest import TestCase

from mock import Mock, patch
from tempfile import mktemp

from gofer.common import Thread as GThread
from gofer.common import Local as GLocal
from gofer.common import Singleton, ThreadSingleton, Options
from gofer.common import synchronized, conditional, released
from gofer.common import mkdir, rmdir, unlink, nvl, valid_path
from gofer.common import List
from gofer.common import new, newT
from gofer.compat import str


class Thing(metaclass=Singleton):

    def __init__(self, n1, n2, a=0, b=0):
        super(Thing, self).__init__()
        self.__mutex = Mock()
        self.name = 'Elmer' + unichr(255) + 'Fudd'
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b

    def __str__(self):
        return str(self.name)


class Thing2(metaclass=Singleton):

    def __init__(self, n1, n2, a=0, b=0):
        super(Thing2, self).__init__()
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b


class ThingT(metaclass=ThreadSingleton):

    def __init__(self, n1, n2, a=0, b=0):
        self.__mutex = Mock()
        self.n1 = n1
        self.n2 = n2
        self.a = a
        self.b = b


class ThingT2(metaclass=ThreadSingleton):

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


class Thing4(object):

    @released
    def bar(self):
        pass


class Thing5(object):
    pass


class Thing6:
    pass


class Teststr(TestCase):

    def test_str(self):
        str(Thing(1, 2))


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


class TestRmdir(TestCase):

    @patch('os.rmdir')
    def test_rm(self, _rmdir):
        path = '/tmp/dir'
        rmdir(path)
        _rmdir.assert_called_once_with(path)

    @patch('os.rmdir')
    def test_not_exist(self, _rmdir):
        path = '/tmp/dir'
        exception = OSError()
        exception.errno = errno.ENOENT
        _rmdir.side_effect = exception
        rmdir(path)

    @patch('os.rmdir')
    def test_failed(self, _rmdir):
        path = '/tmp/dir'
        _rmdir.side_effect = OSError()
        self.assertRaises(OSError, rmdir, path)


class TestUnlink(TestCase):

    @patch('os.unlink')
    def test_unlink(self, _unlink):
        path = '/tmp/file'
        unlink(path)
        _unlink.assert_called_once_with(path)

    @patch('os.unlink')
    def test_not_exist(self, _unlink):
        path = '/tmp/file'
        exception = OSError()
        exception.errno = errno.ENOENT
        _unlink.side_effect = exception
        unlink(path)

    @patch('os.unlink')
    def test_failed(self, _unlink):
        path = '/tmp/file'
        _unlink.side_effect = OSError()
        self.assertRaises(OSError, unlink, path)


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
        expected = "['A', 1, 1.0, True, ('bool', True), ('float', 1.0), ('int', 1), ('string', '')]"

        # validation
        self.assertEqual(expected, key)


class TestThread(TestCase):

    def test_init(self):
        thread = GThread()
        event = getattr(thread, thread.ABORT)
        self.assertTrue(isinstance(event, type(Event())))

    @patch('gofer.common.current_thread')
    def test_current(self, current):
        self.assertEqual(GThread.current(), current.return_value)

    @patch('gofer.common.Thread.join')
    @patch('gofer.common.Thread.abort')
    @patch('threading.Thread.start')
    def test_start(self, start, abort, join):
        def _register(handler, *args):
            handler(*args)
        thread = GThread()
        with patch('atexit.register') as register:
            register.side_effect = _register
            thread.start()
        start.assert_called_once_with()
        self.assertTrue(register.called)
        abort.assert_called_once_with()
        join.assert_called_once_with()

    @patch('gofer.common.current_thread')
    def test_aborted(self, current):
        thread = GThread()
        current.return_value = thread
        event = getattr(thread, thread.ABORT)
        self.assertEqual(GThread.aborted(), event.isSet())
        # abort
        event.set()
        self.assertEqual(GThread.aborted(), event.isSet())

    def test_abort(self):
        thread = GThread()
        event = getattr(thread, thread.ABORT)
        self.assertFalse(event.isSet())
        thread.abort()
        self.assertTrue(event.isSet())


class TestThreadSingleton(TestCase):

    def test_all(self):
        _all = ThreadSingleton.all()
        self.assertTrue(isinstance(_all, dict))

    def test_purge(self):
        things = {
            'A': 1,
            'B': 2,
        }
        _all = ThreadSingleton.all()
        _all.clear()
        _all.update(things)
        purged = ThreadSingleton.purge()
        self.assertEqual(tuple(things.values()), tuple(purged))
        self.assertEqual(ThreadSingleton.all(), {})

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

        def _enter():
            mutex.acquire()
            return mutex

        def _exit(*unused):
            mutex.release()

        mutex.__enter__ = Mock(side_effect=_enter)
        mutex.__exit__ = Mock(side_effect=_exit)

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

        def _enter():
            condition.acquire()
            return condition

        def _exit(*unused):
            condition.release()

        condition.__enter__ = Mock(side_effect=_enter)
        condition.__exit__ = Mock(side_effect=_exit)
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

    @patch('gofer.common.ThreadSingleton.all')
    def test_released(self, _all):
        things = {
            'A': Mock(),
            'B': Mock(),
            'C': Mock(close=Mock(side_effect=ValueError))
        }
        _all.return_value = things
        thing4 = Thing4()
        thing4.bar()
        for thing in things.values():
            thing.close.assert_called_with()


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


class TestNew(TestCase):

    def test_object(self):
        thing = new(Thing5, dict(a=1, b=2))
        self.assertTrue(isinstance(thing, Thing5))
        self.assertEqual(thing.a, 1)
        self.assertEqual(thing.b, 2)

    def test_type(self):
        thing = new(Thing6, dict(a=1, b=2))
        self.assertTrue(isinstance(thing, Thing6))
        self.assertEqual(thing.a, 1)
        self.assertEqual(thing.b, 2)


class TestList(TestCase):

    def test_all(self):
        _list = List()
        _list.append(2)
        self.assertEqual(_list._list, [2])
        _list.append(3)
        self.assertEqual(_list._list, [2, 3])
        _list.insert(0, 1)
        self.assertEqual(_list._list, [1, 2, 3])
        _list.remove(2)
        self.assertEqual(_list._list, [1, 3])
        self.assertEqual(list(iter(_list)), _list._list)


class TestLocal(TestCase):

    def test_getset(self):
        l = GLocal()
        l.name = 'john'
        l.age = 10
        self.assertEqual(l.name, 'john')
        self.assertEqual(l.age, 10)

        def test():
            l.name = 'jane'
            l.age = 44
            self.assertEqual(l.name, 'jane')
            self.assertEqual(l.age, 44)

        t = Thread(target=test)
        t.start()
        t.join()

        self.assertEqual(l.name, 'john')
        self.assertEqual(l.age, 10)

    def test_default(self):
        l = GLocal(name='john', age=10, other={})
        self.assertEqual(l.name, 'john')
        self.assertEqual(l.age, 10)
        self.assertEqual(l.other, {})

        def test():
            self.assertEqual(l.name, 'john')
            self.assertEqual(l.age, 10)
            self.assertEqual(l.other, {})
            l.other['weight'] = 150

        t = Thread(target=test)
        t.start()
        t.join()

        self.assertEqual(l.other, {})


class TestNew(TestCase):

    def test_new(self):
        name = 'elmer'
        age = 30
        T = newT('Person', (object,), {'name': name})
        inst = new(T, {'age': age})
        self.assertTrue(isinstance(inst, T))
        self.assertEqual(T.name, name)
        self.assertEqual(inst.name, name)
        self.assertEqual(inst.age, age)
