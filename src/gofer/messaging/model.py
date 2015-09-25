# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from logging import getLogger

from gofer.common import utf8, json, Options


log = getLogger(__name__)


# --- constants --------------------------------------------------------------

VERSION = '2.0'


# --- exceptions -------------------------------------------------------------


class ModelError(Exception):
    """
    Base for all messaging model exceptions.
    """
    pass


class DocumentError(ModelError):
    """
    Base for all message/document validation.
    """

    def __init__(self, code, description, document, details=None):
        """
        :param code: The validation code.
        :type code: str
        :param document: The document.
        :type document: Document
        :param details: A detailed description of what failed.
        :type details: str
        """
        ModelError.__init__(self, ' : '.join((description or code, details or '')))
        self.code = code
        self.description = description
        self.document = document
        self.details = details


class VersionError(DocumentError):

    CODE = 'model.version'
    DESCRIPTION = 'MODEL: document version not matched'
    DETAILS = 'expected:%s, found:%s'

    def __init__(self, document, expected, found):
        """
        :param document: The invalid document.
        :type document: Document
        :param expected: The expected version.
        :type expected: str
        :param found: The version found in the document.
        :type found: str
        """
        DocumentError.__init__(
            self,
            self.CODE,
            self.DESCRIPTION,
            document,
            self.DETAILS % (expected, found))


# --- utils ------------------------------------------------------------------


def validate(document):
    """
    Determine whether the specified document is valid.
    :param document: The document to evaluate.
    :type document: Document
    :raises DocumentError: when invalid.
    """
    if document.version != VERSION:
        error = VersionError(document, VERSION, document.version)
        log.warn(utf8(error))
        raise error


# --- model ------------------------------------------------------------------


class Document(Options):
    """
    Extends the dict-like object that also provides
    JSON serialization.
    """

    def load(self, s):
        """
        Load using a json string.
        :param s: A json encoded string.
        :type s: str
        """
        d = json.loads(s)
        self.__dict__.update(d)
        return self

    def dump(self):
        """
        Dump to a json string.
        :return: A json encoded string.
        :rtype: str
        """
        def fn(thing):
            if isinstance(thing, Options):
                thing = dict(thing.__dict__)
                for k, v in thing.items():
                    thing[k] = fn(v)
                return thing
            if isinstance(thing, dict):
                thing = dict(thing)
                for k, v in thing.items():
                    thing[k] = fn(v)
                return thing
            if isinstance(thing, (tuple, list)):
                thing = [fn(e) for e in thing]
                return thing
            return thing
        d = fn(self)
        return json.dumps(d, sort_keys=True)
