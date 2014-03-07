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

from hashlib import sha256
from logging import getLogger
from base64 import b64encode, b64decode

from gofer.constants import AUTHENTICATION
from gofer.messaging.model import Document, InvalidDocument


log = getLogger(__name__)


class ValidationFailed(InvalidDocument):
    """
    Message validation failed.
    """

    def __init__(self, details=None):
        """
        :param details: A detailed description.
        :type details: str
        """
        InvalidDocument.__init__(self, AUTHENTICATION, '{}', details)


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

    def validate(self, uuid, digest, signature):
        """
        Validate the specified message and signature.
        :param uuid: The uuid of the sender.
        :type uuid: str
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
        h.update(message)
        digest = h.hexdigest()
        signature = authenticator.sign(digest)
        signed = Document(message=message, signature=encode(signature))
        message = signed.dump()
    except Exception, e:
        log.info(str(e))
        log.debug(message, exc_info=True)
    return message


def validate(authenticator, uuid, message):
    """
    Validate the document using the specified validator.
    signed document:
      {
        message: <message>,
        signature: <signature>
      }
    :param uuid: The destination uuid.
    :type uuid: str
    :param authenticator: A message authenticator.
    :type authenticator: Authenticator
    :param message: A json encoded AMQP message.
    :rtype message: str
    :return: The authenticated document.
    :rtype: Document
    :raises ValidationFailed: when message is not valid.
    """
    if not message:
        return
    document, original, signature = peal(message)
    try:
        if authenticator:
            h = sha256()
            h.update(original)
            digest = h.hexdigest()
            authenticator.validate(uuid, digest, decode(signature))
        return document
    except ValidationFailed, failed:
        failed.document = original
        raise failed
    except Exception, e:
        details = str(e)
        log.info(details)
        log.debug(details, exc_info=True)
        failed = ValidationFailed(details)
        failed.document = original
        raise failed


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
    document = Document()
    document.load(message)
    signature = document.signature
    original = document.message
    if original:
        document = Document()
        document.load(original)
    else:
        original = message
    return document, original, signature


def encode(signature):
    if signature:
        return b64encode(signature)
    else:
        return ''


def decode(signature):
    if signature:
        return b64decode(signature)
    else:
        return ''
