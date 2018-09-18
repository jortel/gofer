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
Message authentication plumbing.
"""

from base64 import b64encode, b64decode
from hashlib import sha256
from logging import getLogger

from gofer.compat import str
from gofer.messaging.model import Document, DocumentError


log = getLogger(__name__)


class ValidationFailed(DocumentError):
    """
    Message validation failed.
    """

    CODE = 'security.authentication'
    DESCRIPTION = 'SECURITY: message authentication failed'

    def __init__(self, details=None, document=None):
        """
        :param details: A detailed description.
        :type details: str
        :param document: The (optional) invalid document.
        :type document: Document
        """
        DocumentError.__init__(
            self,
            self.CODE,
            self.DESCRIPTION,
            document or Document(),
            details)


class Authenticator(object):
    """
    Document the message authenticator API.
    """

    def sign(self, digest):
        """
        Sign the specified message.
        :param digest: An AMQP message digest.
        :type digest: str
        :return: The message signature.
        :rtype: str
        """
        raise NotImplementedError()

    def validate(self, document, digest, signature):
        """
        Validate the specified message and signature.
        :param document: The original signed document.
        :type document: Document
        :param digest: An AMQP message digest.
        :type digest: str
        :param signature: A message signature.
        :type signature: str
        :raises ValidationFailed: when message is not valid.
        """
        raise NotImplementedError()


def sign(authenticator, message):
    """
    Sign the message using the specified validator.
    signed document:
      {
        message: <message>,
        signature: <signature>
      }
    :param authenticator: A message authenticator.
    :type authenticator: Authenticator
    :param message: A (signed) json encoded AMQP message.
    :rtype message: str
    """
    if not authenticator:
        return message
    try:
        h = sha256()
        h.update(message.encode('utf8'))
        digest = h.hexdigest()
        signature = authenticator.sign(digest)
        signed = Document(message=message, signature=encode(signature))
        message = signed.dump()
    except Exception as e:
        log.info(str(e))
        log.debug(message, exc_info=True)
    return message


def validate(authenticator, message):
    """
    Validate the document using the specified validator.
    signed document:
      {
        message: <message>,
        signature: <signature>
      }
    :param authenticator: A message authenticator.
    :type authenticator: Authenticator
    :param message: A json encoded AMQP message.
    :rtype message: str
    :return: The authenticated document.
    :rtype: Document
    :raises ValidationFailed: when message is not valid.
    """
    document, original, signature = peal(message)
    try:
        if authenticator:
            h = sha256()
            h.update(original.encode('utf8'))
            digest = h.hexdigest()
            authenticator.validate(document, digest, decode(signature))
        return document
    except ValidationFailed as de:
        de.document = document
        log.info(str(de))
        raise de
    except Exception as e:
        details = str(e)
        log.info(details)
        log.debug(details, exc_info=True)
        de = ValidationFailed(details, document)
        raise de


def peal(message):
    """
    Peal the incoming message. The message one of:
     - A signed document:
        {
          message: <message>,
          signature: <signature>
        }
     - A plain (unsigned) RMI request.
    Returns:
    - The document to be passed along.
    - The original (signed) AMQP message to be validated.
    - The signature.
    :param message: A json encoded AMQP message.
    :type message: str
    :return: tuple of: (document, original, signature)
    :rtype: tuple
    """
    document = load(message)
    signature = document.signature
    original = document.message
    if original:
        document = load(original)
    else:
        original = message
    return document, original, signature


def load(json):
    """
    Load the json document.
    Decoding errors are intentionally ignored.
    :param json: A json string.
    :type json: str
    :return: The loaded document.
    :rtype: Document
    """
    document = Document()
    try:
        document.load(json)
    except (TypeError, ValueError):
        pass
    return document


def encode(signature):
    if signature:
        return str(
            b64encode(
                bytes(signature, encoding='utf8')),
            encoding='utf8')
    else:
        return ''


def decode(signature):
    if signature:
        return str(
            b64decode(signature),
            encoding='utf8')
    else:
        return ''
