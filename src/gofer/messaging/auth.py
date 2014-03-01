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

from logging import getLogger

from gofer.constants import AUTHENTICATION
from gofer.messaging.model import Document, InvalidDocument


log = getLogger(__name__)


class ValidationFailed(InvalidDocument):
    """
    Message validation failed.
    """

    def __init__(self, message, details):
        """
        :param message: The AMQP message that failed.
        :type message: str
        :param details: A detailed description.
        :type details: str
        """
        InvalidDocument.__init__(self, AUTHENTICATION, message, details)


class Authenticator(object):
    """
    Document the message authenticator API.
    """

    def sign(self, message):
        """
        Sign the specified message.
        :param message: An AMQP message body.
        :type message: str
        :return: The message signature.
        :rtype: str
        """
        raise NotImplementedError()

    def validate(self, uuid, message, signature):
        """
        Validate the specified message and signature.
        :param uuid: The uuid of the sender.
        :type uuid: str
        :param message: An AMQP message body.
        :type message: str
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
        signature: <signature>,
        payload: <payload>
      }
    :param authenticator: A message authenticator.
    :type authenticator: Authenticator
    :param message: A (signed) json encoded AMQP message.
    :rtype message: str
    """
    if not authenticator:
        return message
    try:
        signature = authenticator.sign(message)
        signed = Document(signature=signature, payload=message)
        message = signed.dump()
    except Exception:
        log.debug(message, exc_info=True)
    return message


def validate(authenticator, uuid, message):
    """
    Validate the document using the specified validator.
    signed document:
      {
        signature: <signature>,
        payload: <payload>
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
    try:
        signed = Document()
        signed.load(message)
        signature = signed.signature
        payload = signed.payload
        document = Document()
        if payload:
            document.load(payload)
        else:
            document = signed
        if authenticator:
            authenticator.validate(uuid, payload, signature)
        return document
    except ValidationFailed:
        raise
    except Exception:
        details = 'authenticator failed'
        log.debug(details, exc_info=True)
        raise ValidationFailed(message, details)
