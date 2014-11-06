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

from mock import Mock, patch, call

from gofer.config import Config, ValidationException
from gofer.messaging.adapter.descriptor import DEFAULT, SCHEMA, Descriptor


class TestLoad(TestCase):

    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('gofer.messaging.adapter.descriptor.Descriptor')
    def test_load(self, _descriptor, _isfile, _listdir):
        path = 'path-1'
        files = [
            ('file-1', True),
            ('file-2', True),
            ('file-3', True),
            ('dir--1', False),
            ('dir--2', False),
            ('file-4', True),
        ]
        descriptors = [
            Mock(main=Mock(priority='3')),
            Mock(main=Mock(priority='2')),
            Mock(main=Mock(priority='1')),
            ValidationException(None),
        ]
        _listdir.return_value = [f[0] for f in files]
        _isfile.side_effect = [f[1] for f in files]
        _descriptor.side_effect = descriptors

        loaded = Descriptor.load(path)

        self.assertEqual(loaded, descriptors[:-1][::-1])
        self.assertEqual(
            _descriptor.call_args_list,
            [
                call('path-1/file-1'),
                call('path-1/file-2'),
                call('path-1/file-3'),
                call('path-1/file-4')
            ])

    @patch('gofer.messaging.adapter.descriptor.Config')
    def test_init(self, _config):
        path = 'path-1'
        package = 'a.b.c'
        provides = 'good,bad,ugly'
        config = {
            'main': {
                'package': package,
                'provides': provides
            }
        }
        _config.side_effect = [
            Config(DEFAULT),
            Config(config)
        ]

        descriptor = Descriptor(path)

        self.assertEqual(descriptor.path, path)
        self.assertEqual(descriptor.main.enabled, DEFAULT['main']['enabled'])
        self.assertEqual(descriptor.main.package, package)
        self.assertEqual(descriptor.main.provides, provides)
        self.assertEqual(descriptor.provides, provides.split(','))

    @patch('gofer.messaging.adapter.descriptor.Config')
    def test_init_invalid(self, _config):
        path = 'path-1'
        _config.side_effect = [
            Config(DEFAULT),
            Config({})
        ]

        self.assertRaises(ValidationException, Descriptor, path)