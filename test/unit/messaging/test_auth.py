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

from hashlib import sha256
from unittest import TestCase

from mock import patch, Mock

from gofer.messaging.auth import ValidationFailed, Authenticator
from gofer.messaging.auth import sign, validate
from gofer.messaging.auth import peal, encode, decode


class Test(TestCase):

    def test_validation_failed(self):
        details = 'just failed'
        f = ValidationFailed(details=details)
        self.assertEqual(f.code, ValidationFailed.CODE)
        self.assertEqual(f.document, '{}')
        self.assertEqual(f.args[0], ' : '.join((ValidationFailed.DESCRIPTION, details)))


class TestAuthenticator(TestCase):

    def test_signatures(self):
        digest = '1234'
        document = 'henry-ford'
        signature = 'bing-crosby'
        auth = Authenticator()
        self.assertRaises(NotImplementedError, auth.sign, digest)
        self.assertRaises(NotImplementedError, auth.validate, document, digest, signature)


class TestSign(TestCase):

    @patch('gofer.messaging.auth.encode', side_effect=encode)
    def test_sign(self, encode):
        message = '{"A":1}'
        signature = 'KLAJDF988R'
        authenticator = Mock()
        authenticator.sign.return_value = signature

        # functional test
        signed = sign(authenticator, message)

        # validation
        h = sha256()
        h.update(message)
        authenticator.sign.assert_called_once_with(h.hexdigest())
        encode.assert_called_once_with(signature)
        self.assertEqual(signed, '{"message": "{\\"A\\":1}", "signature": "S0xBSkRGOTg4Ug=="}')

    def test_no_authenticator(self):
        message = 'howdy partner'
        signed = sign(None, message)
        self.assertEqual(signed, message)

    @patch('gofer.messaging.auth.sha256')
    def test_signing_exception(self, sha):
        message = 'howdy partner'
        sha.side_effect = ImportError
        signed = sign(Authenticator(), message)
        self.assertEqual(signed, message)


class TestValidation(TestCase):

    @patch('gofer.messaging.auth.decode', side_effect=decode)
    def test_validate(self, decode):
        signature = 'S0xBSkRGOTg4Ug=='
        message = '{"message": "{\\"A\\":1}", "signature": "%s"}' % signature
        authenticator = Mock()

        # functional test
        validated = validate(authenticator, message)

        # validation
        decode.assert_called_once_with(signature)
        self.assertEqual(1, validated['A'])

    def test_validate_failed(self):
        message = '[]'
        authenticator = Mock()
        authenticator.validate.side_effect = ValidationFailed

        # functional test
        try:
            validate(authenticator, message)
            self.assertTrue(False, msg='validation exception expected')
        except ValidationFailed, e:
            self.assertEqual(e.document, message)

    def test_validate_exception(self):
        message = '[]'
        reason = 'this is bad'
        authenticator = Mock()
        authenticator.validate.side_effect = ValueError(reason)

        # functional test
        try:
            validate(authenticator, message)
            self.assertTrue(False, msg='validation exception expected')
        except ValidationFailed, e:
            self.assertEqual(e.details, reason)
            self.assertEqual(e.document, message)

    def test_no_message(self):
        validated = validate(None, None)
        self.assertEqual(validated, None)


class TestPeal(TestCase):

    def test_signed(self):
        message = '{"message": "{\\"A\\":1}", "signature": "test-signature"}'
        document, original, signature = peal(message)
        self.assertEqual(document['A'], 1)
        self.assertEqual(original, '{"A":1}')
        self.assertEqual(signature, 'test-signature')

    def test_unsigned(self):
        message = '{"A":1}'
        document, original, signature = peal(message)
        self.assertEqual(document['A'], 1)
        self.assertEqual(original, '{"A":1}')
        self.assertEqual(signature, None)


class TestEncoding(TestCase):

    def test_encode(self):
        encoded = encode('howdy')
        self.assertEqual(encoded, 'aG93ZHk=')

    def test_encode_nosignature(self):
        self.assertEqual(encode(None), '')

    def test_decode(self):
        signature = 'aG93ZHk='
        decoded = decode(signature)
        self.assertEqual(decoded, 'howdy')

    def test_decode_no_signature(self):
        self.assertEqual(decode(''), '')