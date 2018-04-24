#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

"""
Provides decorator collator classes.
"""

from gofer import NAME, inspection


class Collator:
    """
    Decorated method/function collator.

    Attributes:
        classes (dict): Dictionary {class: [(function, options)]}
        functions (dict): Dictionary {module: [(function, options)]}
    """

    def __init__(self):
        self.classes = {}
        self.functions = {}

    def __call__(self, functions):
        """
        Collate functions by module|class.

        Args:
            functions (dict): Dictionary of {function: {options}}

        Returns:
            tuple: of ([Class], [Module])
        """
        classes = []
        self.classes.clear()
        self.functions.clear()
        for fn, options in functions.items():
            mod = inspection.module(fn)
            classes.extend(inspection.classes(mod))
            self._bind(classes, fn, options)
        return list(self.classes.values()), list(self.functions.values())

    def _bind(self, classes, fn, options):
        """
        Bind the function (fn) to its class when part of a method
        for to it's module for unbound function.

        This populates the self.classes and self.functions dictionaries.

        Args:
            classes (list): A list of know classes.
            fn (function): A function to bind.
            options (dict): Options associated with a decorated function.
        """
        for name, cls in classes:
            for _, function_ in inspection.methods(cls):
                if function_ == fn:
                    container = self.classes.setdefault(cls.__name__, Class(cls))
                    container += Method(fn, options)
                    return
        mod = inspection.module(fn)
        container = self.functions.setdefault(mod.__name__, Module(mod))
        container += Function(fn, options)


class Member(object):
    """
    Member of a container.

    Attributes:
        impl (function): Real object.
        options (dict): decorator options.
    """

    def __init__(self, impl, options=None):
        """
        Args:
            impl (function): Real function.
            options (dict): decorator options.
        """
        self.impl = impl
        self.options = options
        self.container = None

    @property
    def name(self):
        return self.impl.__name__

    @property
    def fninfo(self):
        return getattr(self.impl, NAME, None)

    def __eq__(self, other):
        return other.impl == self.impl

    def __lt__(self, other):
        return self.name < other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __call__(self, *args, **kwargs):
        return self.impl(*args, **kwargs)

    def __hash__(self):
        return hash(self.impl)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.container:
            return '{}.{}'.format(self.container.name, self.name)
        else:
            return self.name


class Function(Member):
    """
    Function.

    Attributes:
        impl (function): Real function.
        options (dict): decorator options.
    """

    @property
    def module(self):
        return self.container

    @property
    def signature(self):
        return inspection.signature(self.impl)

    def __str__(self):
        return '{}{}'.format(self.name, self.signature)

    def __call__(self, *args, **kwargs):
        return self.impl(*args, **kwargs)


class Method(Member):
    """
    Method.
    """

    @property
    def class_(self):
        return self.container

    @property
    def signature(self):
        return inspection.signature(self.impl)

    def __str__(self):
        return '{}{}'.format(self.name, self.signature)

    def __call__(self, *args, **kwargs):
        return self.impl(self.container.inst, *args, **kwargs)


class MemberNotFound(Exception):
    """
    Method or Function not found.
    """

    def __str__(self):
        return '{} not found.'.format(self.args[0])


class Container(object):

    def _populate(self, colleciton):
        if colleciton:
            for m in colleciton.values():
                m.container = self
            return colleciton
        else:
            return {}

    def __init__(self, impl, collection=None):
        self._collection = self._populate(collection)
        self.impl = impl
        self.inst = None

    @property
    def name(self):
        return self.impl.__name__

    @property
    def name(self):
        return self.impl.__name__

    def __hash__(self):
        return hash(self.name)

    def __iadd__(self, member):
        self._collection[member.name] = member
        member.container = self
        return self

    def __getitem__(self, name):
        try:
            return self._collection[name]
        except KeyError:
            raise MemberNotFound(name)

    def __repr__(self):
        return '<{}> {}'.format(self.__class__.__name__.lower(), self.name)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.name < other.name

    def __iter__(self):
        return iter(self._collection.values())

    def __call__(self, *args, **kwargs):
        self.inst = self.impl
        return self

    def call(self, name, *args, **kwargs):
        member = self[name]
        return member(*args, **kwargs)


class Module(Container):
    """
    A module-like of functions.

    Attributes:
        functions (dict): Dictionary of functions.
        impl (module): A real module.
    """

    def __init__(self, impl, functions=None):
        """
        Args:
            functions (dict): Dictionary of functions.
            impl (module): A real module.
        """
        super(Module, self).__init__(impl, functions)

    @property
    def functions(self):
        return self._collection


class Class(Container):
    """
    A class-like of methods (functions).

    Attributes:
        methods (dict): Dictionary of methods.
        impl (module): A real module.
    """

    def __init__(self, impl, methods=None):
        """
        Args:
            methods (dict): Dictionary of methods.
            impl (module): A real module.
        """
        super(Class, self).__init__(impl, methods)

    @property
    def methods(self):
        return self._collection

    def __call__(self, *args, **kwargs):
        self.inst = self.impl(*args, **kwargs)
        return self

    def call(self, name, *args, **kwargs):
        member = self[name]
        return member(*args, **kwargs)
