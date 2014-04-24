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

from mock import patch, Mock
from StringIO import StringIO
from copy import deepcopy as clone

from gofer.config import *


SCHEMA = (
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

VALID = {
    'section1': {
        'property1': '10',
        'property2': 'http://redhat.com',
        'property3': 'howdy'
    },
    'section2': {
        'property1': '10',
        'property2': '1',
        'property3': '0'
    }
}

MINIMAL = {
    'section1': {
        'property1': '10',
        'property2': 'http://redhat.com',
        'property3': 'howdy'
    }
}

MINIMAL2 = {
    'section1': {
        'property1': '10',
        'property2': 'http://redhat.com',
        'property3': 'howdy'
    },
    'section2': {
        'property3': '0'
    }
}

EXTRA = {
    'section1': {
        'property1': '10',
        'property2': 'http://redhat.com',
        'property3': 'howdy',
        'property4': 'unknown',
        'property5': 'unknown'
    },
    'phone': {
        'cell': '1234',
        'home': '5678'
    }
}

MISSING_SECTION = {
    'phone': {
        'cell': '1234',
        'home': '5678'
    }
}

MISSING_PROPERTY = {
    'section1': {
        'property1': '10',
        'property3': 'howdy'
    }
}

INVALID_PROPERTY = {
    'section1': {
        'property1': 'should be a number',
        'property2': 'http://redhat.com',
        'property3': 'howdy'
    }
}

INI_VALID = """
[section1]
property1=10
property2=http://redhat.com
property3=howdy
[section2]
property1=10
property2=1
property3=0
"""


class TestUtils(TestCase):

    def test_get_bool(self):
        self.assertTrue(get_bool('yes'))
        self.assertTrue(get_bool('true'))
        self.assertTrue(get_bool('1'))
        self.assertFalse(get_bool('no'))
        self.assertFalse(get_bool('false'))
        self.assertFalse(get_bool('0'))
        self.assertFalse(get_bool(''))
        self.assertRaises(ValueError, get_bool, 'hello')


class TestExceptions(TestCase):

    def test_validation_exception(self):
        # path
        e = ValidationException('hello', '/path')
        self.assertEqual(e.description, 'hello')
        self.assertEqual(e.path, '/path')
        self.assertEqual(e.message, 'hello in: /path')
        # no path
        e = ValidationException('hello')
        self.assertEqual(e.description, 'hello')
        self.assertEqual(e.path, None)
        self.assertEqual(e.message, 'hello')

    def test_section_not_found(self):
        # path
        e = SectionNotFound('test', '/path')
        self.assertEqual(e.description, 'Required section [test], not found')
        self.assertEqual(e.path, '/path')
        self.assertEqual(e.name, 'test')
        self.assertEqual(e.message, 'Required section [test], not found in: /path')
        # no path
        e = SectionNotFound('test')
        self.assertEqual(e.description, 'Required section [test], not found')
        self.assertEqual(e.path, None)
        self.assertEqual(e.name, 'test')
        self.assertEqual(e.message, 'Required section [test], not found')

    def test_property_not_found(self):
        # path
        e = PropertyNotFound('test', '/path')
        self.assertEqual(e.description, 'Required property [test], not found')
        self.assertEqual(e.path, '/path')
        self.assertEqual(e.name, 'test')
        self.assertEqual(e.message, 'Required property [test], not found in: /path')
        # no path
        e = PropertyNotFound('test')
        self.assertEqual(e.description, 'Required property [test], not found')
        self.assertEqual(e.path, None)
        self.assertEqual(e.name, 'test')
        self.assertEqual(e.message, 'Required property [test], not found')

    def test_property_not_valid(self):
        # path
        e = PropertyNotValid('age', 'xxx', '[0-9]+', '/path')
        self.assertEqual(e.description, 'Property: age value "xxx" must be: [0-9]+')
        self.assertEqual(e.path, '/path')
        self.assertEqual(e.name, 'age')
        self.assertEqual(e.value, 'xxx')
        self.assertEqual(e.pattern, '[0-9]+')
        self.assertEqual(e.message, 'Property: age value "xxx" must be: [0-9]+ in: /path')
        # no path
        e = PropertyNotValid('age', 'xxx', '[0-9]+')
        self.assertEqual(e.description, 'Property: age value "xxx" must be: [0-9]+')
        self.assertEqual(e.path, None)
        self.assertEqual(e.name, 'age')
        self.assertEqual(e.value, 'xxx')
        self.assertEqual(e.pattern, '[0-9]+')
        self.assertEqual(e.message, 'Property: age value "xxx" must be: [0-9]+')


class TestConfig(TestCase):

    @patch('gofer.config.Config.open')
    @patch('gofer.config.Config.update')
    @patch('gofer.config.Config.read')
    def test_init(self, _read, _update, _open):
        path = '/path'
        d = {'A': 1}
        fp = Mock()
        Config(path, d, fp)
        _update.assert_called_with(d)
        _open.assert_called_with([path])
        _read.assert_called_with(fp)

    @patch('__builtin__.open')
    @patch('gofer.config.Config.read')
    def test_open(self, _read, _open):
        _fp = Mock()
        _open.return_value = _fp
        path = '/path'
        cfg = Config()
        cfg.open(path)
        _open.assert_called_with(path)
        _read.assert_called_with(_fp)
        _fp.close.assert_called_with()

    def test_read(self):
        fp = StringIO(INI_VALID)
        cfg = Config()
        cfg.read(fp)
        self.assertEqual(cfg, VALID)

    def test_update(self):
        expected = {}
        base = {'main': {'name': 'elmer', 'age': 50}}
        phone = {'phone': {'cell': '1234'}}
        cfg = Config(base)
        cfg.update(phone)
        expected.update(base)
        # add [phone]
        expected.update(phone)
        self.assertEqual(cfg, expected)
        phone2 = {'phone': {'home': '5678'}}
        # update [phone]
        cfg.update(phone2)
        expected['phone'].update(phone2['phone'])
        self.assertEqual(cfg, expected)

    @patch('gofer.config.Graph')
    def test_graph(self, _graph):
        cfg = Config()
        graph = cfg.graph()
        _graph.assert_called_with(cfg, False)
        self.assertEqual(graph, _graph())

    @patch('gofer.config.Graph')
    def test_strict_graph(self, _graph):
        cfg = Config()
        graph = cfg.graph(strict=True)
        _graph.assert_called_with(cfg, True)
        self.assertEqual(graph, _graph())

    @patch('gofer.config.Validator')
    def test_validate(self, _validator):
        cfg = Config()
        cfg.validate(SCHEMA)
        _validator.assert_called_with(SCHEMA)
        _validator().validate.assert_called_with(cfg)

    def test_setitem(self):
        key = 'test-key'
        section = {'A': 1}
        cfg = Config()
        # valid
        cfg[key] = section
        self.assertEqual(cfg[key], section)
        # invalid
        self.assertRaises(ValueError, cfg.__setitem__, key, 100)


class TestValidator(TestCase):

    def test_init(self):
        schema = (1, 2, 3)
        v = Validator(schema)
        self.assertEqual(v.schema, schema)

    def test_validate_real(self):
        v = Validator(SCHEMA)
        # valid
        v.validate(Config(VALID))
        v.validate(Config(MINIMAL))
        v.validate(Config(MINIMAL2))
        undef = v.validate(Config(EXTRA))
        self.assertEqual(undef, (['phone'], ['section1.property4', 'section1.property5']))
        # missing section
        self.assertRaises(SectionNotFound, v.validate, Config(MISSING_SECTION))
        # missing property
        self.assertRaises(PropertyNotFound, v.validate, Config(MISSING_PROPERTY))
        # invalid property
        self.assertRaises(PropertyNotValid, v.validate, Config(INVALID_PROPERTY))

    @patch('gofer.config.Validator.undefined')
    @patch('gofer.config.Section')
    def test_validate(self, _section, _undefined):
        _s1 = Section(SCHEMA[0])
        _s1.validate = Mock()
        _s2 = Section(SCHEMA[1])
        _s2.validate = Mock()
        _section.side_effect = [_s1, _s2]
        v = Validator(SCHEMA)
        cfg = Config(VALID)
        v.validate(cfg)
        self.assertEqual(_section.call_count, 2)
        _s1.validate.assert_called_once_with(cfg[_s1.name])
        _s2.validate.assert_called_once_with(cfg[_s2.name])
        _undefined.assert_called_with(cfg)

    def test_undefined(self):
        v = Validator(SCHEMA)
        undef = v.undefined(Config(EXTRA))
        self.assertEqual(undef, (['phone'], ['section1.property4', 'section1.property5']))


class TestPatterns(TestCase):

    def setUp(self):
        Patterns.patterns = {}

    def tearDown(self):
        Patterns.patterns = {}

    @patch('gofer.config.Patterns._Patterns__mutex')
    def test_get(self, _mutex):
        # new pattern
        p = Patterns.get(NUMBER)
        self.assertEqual(_mutex.acquire.call_count, 1)
        self.assertEqual(_mutex.acquire.call_count, _mutex.release.call_count)
        self.assertEqual(p, re.compile(NUMBER))
        self.assertEqual(Patterns.patterns[NUMBER], p)
        # existing pattern
        p = Patterns.get(NUMBER)
        self.assertEqual(_mutex.acquire.call_count, 2)
        self.assertEqual(_mutex.acquire.call_count, _mutex.release.call_count)
        self.assertEqual(p, re.compile(NUMBER))
        self.assertEqual(Patterns.patterns[NUMBER], p)

    def test_split(self):
        # single
        pattern = 'test-pattern'
        regex, flags = Patterns.split(pattern)
        self.assertEqual(regex, pattern)
        self.assertEqual(flags, 0)
        # tuple
        pattern = ('test-pattern', 'flags')
        regex, flags = Patterns.split(pattern)
        self.assertEqual(regex, pattern[0])
        self.assertEqual(flags, pattern[1])

    @patch('gofer.config.Patterns._Patterns__mutex')
    def test_lock(self, _mutex):
        Patterns._Patterns__lock()
        _mutex.acquire.assert_called_once_with()
        self.assertFalse(_mutex.release.called)

    @patch('gofer.config.Patterns._Patterns__mutex')
    def test_unlock(self, _mutex):
        Patterns._Patterns__unlock()
        _mutex.release.assert_called_once_with()
        self.assertFalse(_mutex.acquire.called)


class TestSection(TestCase):

    def test_init(self):
        definition = SCHEMA[0]
        section = Section(definition)
        self.assertEqual(section.name, definition[0])
        self.assertEqual(section.required, definition[1])
        self.assertEqual(section.properties, definition[2])

    @patch('gofer.config.Section.valid_property')
    def test_validate(self, _valid_property):
        definition = SCHEMA[0]
        section = Section(definition)
        # validate None
        self.assertRaises(SectionNotFound, section.validate, None)
        # validate real
        section.validate(VALID['section1'])
        self.assertEqual(_valid_property.call_count, len(section.properties))
        for property in section.properties:
            _valid_property.assert_any_call(VALID['section1'], property)

    @patch('gofer.config.Property.validate')
    def test_valid_property(self, _validate):
        definition = SCHEMA[0]
        section = Section(definition)
        # not found
        _validate.side_effect = PropertyNotFound('')
        self.assertRaises(PropertyNotFound, section.valid_property, {}, section.properties[0])
        # found
        _validate.reset_mock()
        _validate.side_effect = None
        section.valid_property({'property1': '100'}, section.properties[0])
        _validate.assert_called_with('100')


class TestProperty(TestCase):

    def test_init(self):
        definition = SCHEMA[0][2][0]
        p = Property(definition)
        self.assertEqual(p.name, definition[0])
        self.assertEqual(p.required, definition[1])
        self.assertEqual(p.pattern, definition[2])

    def test_validate(self):
        definition = SCHEMA[0][2][0]
        p = Property(definition)
        # real: valid
        p.validate('100')
        # real: invalid
        self.assertRaises(PropertyNotValid, p.validate, 'hello')


class TestGraph(TestCase):

    def test_init(self):
        graph = Graph(MINIMAL)
        self.assertEqual(graph._Graph__dict, MINIMAL)
        self.assertFalse(graph._Graph__strict)
        # strict
        graph = Graph(MINIMAL, strict=True)
        self.assertEqual(graph._Graph__dict, MINIMAL)
        self.assertTrue(graph._Graph__strict)

    def test_accessing(self):
        graph = Graph(clone(MINIMAL))
        # property: found
        self.assertEqual(graph.section1.property1, '10')
        # property: not found
        self.assertEqual(graph.section1.propertyXX, None)
        self.assertEqual(graph.section10.property1, None)
        # section: found
        self.assertEqual(repr(graph.section1), repr(MINIMAL['section1']))
        # section: not found
        self.assertEqual(repr(graph.section100), repr({}))

    def test_strict_accessing(self):
        graph = Graph(clone(MINIMAL), strict=True)
        # property: found
        self.assertEqual(graph.section1.property1, '10')
        # property: not found
        try:
            unused = graph.section1.propertyXX
            self.assertTrue(False, msg='AttributeError not raised')
        except AttributeError:
            pass
        # section: found
        self.assertEqual(repr(graph.section1), repr(MINIMAL['section1']))
        # section: not found
        try:
            unused = graph.section100
            self.assertTrue(False, msg='AttributeError not raised')
        except AttributeError:
            pass

    def test_iter(self):
        graph = Graph(clone(VALID))
        sections = list(graph)
        self.assertEqual(len(sections), len(VALID))
        self.assertEqual(sections[0], (VALID.items()[0]))
        self.assertEqual(sections[1], (VALID.items()[1]))

    def test_str(self):
        graph = Graph(clone(MINIMAL))
        s = str(graph)
        self.assertEqual(s, '\n[section1]\nproperty1=10\nproperty2=http://redhat.com\nproperty3=howdy')

    def test_repr(self):
        graph = Graph(clone(MINIMAL))
        s = repr(graph)
        self.assertEqual(s, repr(MINIMAL))


class TestGraphSection(TestCase):

    def test_set(self):
        graph = Graph(clone(MINIMAL))
        section = graph.section1
        self.assertTrue(section.thing is None)
        section.thing = 100
        self.assertEqual(section.thing, 100)
        
    def test_get(self):
        graph = Graph(clone(MINIMAL))
        section = graph.section1
        # found
        p1 = section.property1
        self.assertEqual(p1, MINIMAL['section1']['property1'])
        # not found
        p1 = section.foobar
        self.assertTrue(p1 is None)

    def test_strict_get(self):
        graph = Graph(clone(MINIMAL), strict=True)
        section = graph.section1
        # found
        p1 = section.property1
        self.assertEqual(p1, MINIMAL['section1']['property1'])
        # not found
        try:
            unused = section.foobar
            self.assertTrue(False, msg='AttributeError not raised')
        except AttributeError:
            pass

    def test_str(self):
        graph = Graph(clone(MINIMAL))
        s = str(graph.section1)
        self.assertEqual(s, 'property1=10\nproperty2=http://redhat.com\nproperty3=howdy')

    def test_repr(self):
        graph = Graph(clone(MINIMAL))
        s = repr(graph.section1)
        self.assertEqual(s, repr(MINIMAL['section1']))

    def test_iter(self):
        graph = Graph(clone(MINIMAL))
        properties = list(graph.section1)
        self.assertEqual(properties, MINIMAL['section1'].items())