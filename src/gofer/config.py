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

"""
The entry point into this module is the Config class. It accepts one or more
files to load and after instantiation will be used to access the values within.
The files are loaded in order and the last value for a property is used.

Example usage:
  config = Config('base.conf', 'override.conf')

The Config object also supports validation of the loaded configuration values.
The schema is defined in a nested tuple structure that defines each section
(along with its required/optional flag) and each property within the section.
For each property, its required/optional flag and validation criteria are
specified. Criteria can take the form of one of the constants in this module
or a regular expression.

Example code for defining a schema and validating a config against it:

schema = (
    ('section1', REQUIRED,
        (
            ('property1', REQUIRED, NUMBER),
            ('property2', REQUIRED, 'http://.+'),
            ('property3', REQUIRED, ANY),
        ),
    ),
    ('section2', OPTIONAL,
        (
            ('property1', OPTIONAL, NUMBER),
            ('property2', OPTIONAL, BOOL),
            ('property3', REQUIRED, BOOL),
        ),
    ),
)

cfg = Config('base.conf')
cfg.validate(schema)
"""

import re

from threading import RLock
from iniparse import INIConfig


# -- constants ----------------------------------------------------------------

# Schema Constants
REQUIRED = 1
OPTIONAL = 0
ANY = None
NUMBER = '^\d+$'
BOOL = '(^YES$|^TRUE$|^1$|^NO$|^FALSE$|^0$)', re.I

# Regular expression to test if a value is a valid boolean type
BOOL_RE = re.compile(*BOOL)

# -- utils --------------------------------------------------------------------


def get_bool(value):
    """
    Parses the given value into its boolean representation.
    :param value: value to test
    :type value: str
    :return: true or false depending on what is parsed
    :rtype: bool
    :raise ValueError: if the value is not one of the accepted values for
           indicating a boolean
    """
    if not value:
        return False
    if BOOL_RE.match(value):
        return value.upper() in ('YES', 'TRUE', '1')
    else:
        raise ValueError('%s: must be <bool>' % value)


# -- exceptions ---------------------------------------------------------------


class ValidationException(Exception):

    def __init__(self, name):
        Exception.__init__(self)

        self.name = name
        self.path = ''

    def msg(self, fmt, *args):
        msg = fmt % args
        if self.path:
            msg = '%s in: %s' % (msg, self.path)
        return msg


class SectionNotFound(ValidationException):

    def __str__(self):
        return self.msg('Required section [%s], not found', self.name)


class PropertyException(ValidationException):
    pass


class PropertyNotFound(PropertyException):

    def __str__(self):
        return self.msg('Required property "%s", not found', self.name)


class PropertyNotValid(PropertyException):

    def __init__(self, name, value, pattern):
        PropertyException.__init__(self, name)
        self.value = value
        self.pattern = pattern

    def __str__(self):
        return self.msg(
            'Property: %s value "%s" must be: %s',
            self.name,
            self.value,
            self.pattern)


# -- public -------------------------------------------------------------------


class Config(dict):
    """
    Holds configuration files in the INI format; all properties are in a
    named section and are accessed by specifying both the section name and
    the property name.

    Properties are accessed through a nested dictionary syntax where the first
    item is the section name and the second is the property name. For example,
    to access a property named "server" in section "[main]":

       value = config['main']['enabled']

    Alternatively, a dot notation syntax can be used by first retrieving a
    wrapper on top of the configuration through the graph() method:

       graph = config.graph()
       value = graph.main.enabled
    """

    def __init__(self, *inputs):
        """
        Creates a blank configuration and loads one or more files
        or existing data.

        Values to the inputs parameter can be one of three things:
         - the full path to a file to load (str)
         - file object to read from
         - dictionary whose values will be merged into this instance

        :param inputs: one or more files to load (see above)
        :param options: see above
        """
        super(Config, self).__init__()
        for input in inputs:
            if isinstance(input, basestring):
                self.open([input])
                continue
            if isinstance(input, dict):
                self.update(input)
                continue
            self.read(input)

    def open(self, paths):
        """
        Open and read the files at the specified paths.
        :param paths: A path or list of paths to .conf files
        :type paths: str|list
        """
        if isinstance(paths, basestring):
            paths = (paths,)
        for path in paths:
            with open(path) as fp:
                self.read(fp)

    def read(self, fp):
        """
        Read and parse the fp.
        :param fp: An open file
        :type fp: file-like object.
        """
        cfg = INIConfig(fp)
        for s in cfg:
            section = self.setdefault(s, {})
            for p in cfg[s]:
                v = getattr(cfg[s], p)
                section[p] = v

    def update(self, other):
        """
        Copies sections and properties from "other" into this instance.
        :param other: values to copy into this instance
        :type other: dict
        """
        for k, v in other.items():
            if k in self and isinstance(v, dict):
                self[k].update(v)
            else:
                self[k] = v

    def graph(self, strict=False):
        """
        Get an object representation of this instance. The data is the same,
        however the returned object supports a dot notation for accessing
        values.

        :param strict: Indicates that KeyError should be raised when
            undefined sections or properties are accessed. When
            false, undefined sections are returned as empty dict and
            undefined properties are returned as (None).
        :type strict: bool
        :return: graph object representation of the configuration
        :rtype: Graph
        """
        return Graph(self, strict)

    def validate(self, schema):
        """
        Validates the values in the instance against the given schema.
        :param schema: nested tuples as described in the module docs
        :type schema: tuple
        :return: two list: undefined sections and properties.
        :rtype: tuple
        :raise ValidationException: if the configuration does not pass validation
        """
        v = Validator(schema)
        return v.validate(self)

    def __setitem__(self, name, value):
        """
        Set a section value.
        :param name: A section name.
        :type name: str
        :param value: A section.
        :type value: dict
        """
        if isinstance(value, dict):
            dict.__setitem__(self, name, value)
        else:
            raise ValueError('%s: must be <dict>' % value)


# -- private ------------------------------------------------------------------


class Validator(object):
    """
    The main validation object.
    :ivar schema: An INI schema.
    :type schema: tuple
    """

    def __init__(self, schema):
        """
        :param schema: An INI schema.
        :type schema: tuple
        """
        self.schema = schema

    def validate(self, cfg):
        """
        Validate the specified INI configuration object.
        :param cfg: An INI configuration object.
        :type cfg: Config
        :raise ValidationException: Or failed.
        :return: Two list: undefined sections and properties.
        :rtype: tuple
        """
        for section in self.schema:
            s = Section(section)
            section = cfg.get(s.name)
            s.validate(section)
        return self.undefined(cfg)

    def undefined(self, cfg):
        """
        Report section and properties found in the configuration
        that are not defined in the schema.
        :param cfg: An INI configuration object.
        :type cfg: Config
        :return: Two lists: sections, properties
        :rtype: tuple
        """
        extras = ([],[])
        expected = {}
        for section in [s for s in self.schema]:
            properties = set()
            expected[section[0]] = properties
            for pn in section[2]:
                properties.add(pn[0])
        for sn in cfg:
            session = expected.get(sn)
            if not session:
                extras[0].append(sn)
                continue
            for pn in cfg[sn]:
                if pn not in session:
                    pn = '.'.join((sn, pn))
                    extras[1].append(pn)
        return extras


class Patterns(object):
    """
    Regex pattern cache object.
    Used so we don't compile regular expressions one than once.
    :cvar patterns: The dictionary of compiled patterns.
    :type patterns: dict
    """

    patterns = {}
    __mutex = RLock()

    @classmethod
    def get(cls, regex):
        """
        Get a compiled pattern.
        :param regex: A regular expression.
        :type regex: str|(str,int)
        :return: compiled pattern
        """
        key = regex
        regex, flags = cls.split(regex)
        cls.__lock()
        try:
            p = cls.patterns.get(regex)
            if p is None:
                p = re.compile(regex, flags)
                cls.patterns[key] = p
            return p
        finally:
            cls.__unlock()

    @classmethod
    def split(cls, x):
        if isinstance(x, tuple):
            regex = x[0]
            flags = x[1]
        else:
            regex = x
            flags = 0
        return regex, flags

    @classmethod
    def __lock(cls):
        cls.__mutex.acquire()

    @classmethod
    def __unlock(cls):
        cls.__mutex.release()


class Section(object):
    """
    A section validation object.
    Used to validate INI sections based on schema.
    :ivar name: The section name.
    :type name: str
    :ivar required: Indicates the section is required.
    :type required: bool
    :ivar properties: List of property specifications.
    :type properties: list
    """

    def __init__(self, section):
        """
        :param section: The section schema specification.
            specification: (name, required, properties)
        :type section: tuple
        """
        self.name = section[0]
        self.required = section[1]
        self.properties = section[2]

    def validate(self, section):
        """
        Validate a configuration section object.
        Also validates properties.
        :param section: An INI section object.
        :type section: iniparse.ini.INISection
        :raise SectionException: On failure.
        """
        if section is None:
            if self.required:
                raise SectionNotFound(self.name)
        else:
            for property in self.properties:
                self.valid_property(section, property)

    def valid_property(self, section, property):
        """
        Validate a property specification.
        :param section: An INI section object.
        :type section: iniparse.ini.INISection
        :param property: A property specification.
            format: (name, required, pattern)
        :type property: tuple
        :raise SectionException: On failure.
        """
        p = Property(property)
        try:
            property = section.get(p.name)
            p.validate(property)
        except PropertyException, pe:
            pe.name = '.'.join((self.name, pe.name))
            raise pe


class Property(object):
    """
    A property validation object.
    Used to validate INI sections property objects based on schema.
    :ivar name: The property name.
    :type name: str
    :ivar required: Indicates the property is required.
    :type required: bool
    :ivar pattern: A regex used to validate the property
        value.  A (None) pattern indicates no value validation.
    :type pattern: str
    """

    def __init__(self, property):
        """
        :param property: A property schema specification.
            format: (name, required, pattern)
        :type property: tuple
        """
        self.name = property[0]
        self.required = property[1]
        self.pattern = property[2]

    def validate(self, value):
        """
        Validate a configuration section object.
        Also validates properties.
        :param value: An property value.
        :type value: str
        :raise PropertyException: On failure.
        """
        if value is None:
            if self.required:
                raise PropertyNotFound(self.name)
            return
        if not self.pattern:
            return
        p = Patterns.get(self.pattern)
        match = p.match(value)
        if not match:
            raise PropertyNotValid(self.name, value, self.pattern)


class Graph(object):
    """
    An object graph representation of a configuration.
    Provides access using object attribute (.) dot notation.
    :ivar __dict: The wrapped dictionary.
    :type __dict: dict
    :ivar strict: Indicates that KeyError should be raised when
        undefined sections are accessed.  When false, undefined
        sections are returned as empty dict
    :type strict: bool
    """

    def __init__(self, content, strict=False):
        """
        :param content: The wrapped dictionary.
        :type content: dict
        :param strict: Indicates that KeyError should be raised when
            undefined sections are accessed.  When false, undefined 
            sections are returned as empty dict.
        :type strict: bool
        """
        self.__dict = content
        self.__strict = strict

    def __getattr__(self, name):
        try:
            if self.__strict:
                s = self.__dict[name]
            else:
                s = self.__dict.setdefault(name, {})
            return GraphSection(s, self.__strict)
        except KeyError:
            raise AttributeError(name)

    def __iter__(self):
        return iter(self.__dict)

    def __repr__(self):
        return repr(self.__dict)

    def __str__(self):
        s = []
        for name, section in sorted(self.__dict.items()):
            s.append('\n[%s]' % name)
            gs = GraphSection(section)
            s.append(str(gs))
        return '\n'.join(s)


class GraphSection(object):
    """
    An object graph representation of a section.
    """

    def __new__(cls, content, strict=False):
        """
        :param content: The wrapped dictionary.
        :type content: dict
        :param strict: Indicates that KeyError should be raised when
            undefined sections are accessed.  When false, undefined
            sections are returned as empty dict.
        :type strict: bool
        """

        gs = type(cls.__name__, (object,), {})

        def _set(self, key, value):
            content[key] = value

        def _get(self, name):
            try:
                if strict:
                    return content[name]
                else:
                    return content.get(name)
            except KeyError:
                raise AttributeError(name)

        def _iter(self):
            return iter(content)

        def _repr(self):
            return repr(content)

        def _str(self):
            s = []
            for k, v in content.items():
                s.append('%s=%s' % (k, v))
            return '\n'.join(s)

        gs.__getattr__ = _get
        gs.__setattr__ = _set
        gs.__iter__ = _iter
        gs.__repr__ = _repr
        gs.__str__ = _str

        return gs()
