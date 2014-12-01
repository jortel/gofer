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

from gofer.messaging.model import VERSION, Document, validate
from gofer.messaging.model import InvalidDocument, InvalidVersion


class TestExceptions(TestCase):

    def test_invalid_document(self):
        code = '1'
        description = '2'
        document = '3'
        details = '4'

        # test
        exception = InvalidDocument(code, description, document, details=details)

        # validation
        self.assertEqual(exception.code, code)
        self.assertEqual(exception.args, ('2 : 4',))
        self.assertEqual(exception.document, document)
        self.assertEqual(exception.details, details)

    def test_invalid_version(self):
        document = Document(version='1.0')
        details = '4'

        # test
        exception = InvalidVersion(document, details)

        # validation
        self.assertEqual(exception.code, InvalidVersion.CODE)
        self.assertEqual(exception.args, ('%s : 4' % InvalidVersion.DESCRIPTION,))
        self.assertEqual(exception.document, document.dump())
        self.assertEqual(exception.details, details)


class TestValidate(TestCase):

    def test_valid(self):
        document = Document(version=VERSION)
        validate(document)

    def test_invalid(self):
        document = Document(version=VERSION+'.0')
        self.assertRaises(InvalidVersion, validate, document)


class TestDocument(TestCase):

    def test_load(self):
        s = '{"A": 1}'
        document = Document()
        document.load(s)
        self.assertEqual(document.__dict__, {'A': 1})

    def test_dump(self):
        document = Document(
            A=1,
            B=2,
            C=Document(a=1, b=2),
            D=dict(x=10, y=20),
            E=[1, Document(), dict()],
            F=10,
            G='howdy',
            H=True,
        )
        s = document.dump()
        self.assertEqual(
            s,
            '{"A": 1, "B": 2, "C": {"a": 1, "b": 2}, "D": {"x": 10, "y": 20}, '
            '"E": [1, {}, {}], "F": 10, "G": "howdy", "H": true}')
