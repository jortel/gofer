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
#
# Jeff Ortel <jortel@redhat.com>
#


from mock import patch, Mock


class Module(object):

    def __init__(self):
        pass


class Fake(object):

    def __init__(self, *args, **keywords):
        self.args = args
        self.keywords = keywords


class SideEffect(object):

    def __init__(self, *values):
        self.values = iter(values)

    def __call__(self, *args, **kwargs):
        value = self.values.next()
        if isinstance(value, Mock):
            return value
        if callable(value):
            value = value(*args, **kwargs)
        if isinstance(value, Exception):
            raise value
        return value


class Import(object):

    def __init__(self, package, parent=__import__):
        self.modules = {}
        self.package = package
        self.parent = parent

    def find(self, n, f):
        m = self.modules.setdefault(n, Module())
        if not f:
            return Fake
        for t in f:
            if not hasattr(m, t):
                setattr(m, t, Fake)
        return m

    def __call__(self, name, globals=None, locals=None, fromlist=None, level=-1):
        if not name.startswith(self.package):
            return self.parent(
                name,
                globals or {},
                locals or {},
                fromlist or [],
                level)
        else:
            return self.find(name, fromlist)


class Patch(object):

    def __init__(self, package):
        self.package = package
        self.patch = None

    def __call__(self, fn):
        def inner(_self):
            with self:
                return fn(_self)
        inner.__name__ = fn.__name__
        return inner

    def __enter__(self):
        parent = __import__
        p = patch('__builtin__.__import__')
        mocked = p.__enter__()
        importer = Import(self.package, parent)
        mocked.side_effect = importer
        self.patch = p
        return self

    def __exit__(self, *unused):
        self.patch.__exit__(*unused)
        self.patch = None


def ipatch(package):
    return Patch(package)



