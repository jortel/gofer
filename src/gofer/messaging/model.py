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


import simplejson as json

from uuid import uuid4
from logging import getLogger


log = getLogger(__name__)


# --- constants --------------------------------------------------------------

VERSION = '0.5'


# --- utils ------------------------------------------------------------------


def getuuid():
    return str(uuid4())


def is_valid(request):
    """
    Determine whether the specified request is valid.
    :param request: The envelope to evaluate.
    :type request: Envelope
    :return: True if valid.
    :rtype: bool
    """
    valid = True
    if request.version != VERSION:
        valid = False
        log.warn('version mismatch %s/%s', request.version, VERSION)
    return valid


def search(reader, sn, timeout=90):
    """
    Search the reply queue for the envelope with the matching serial #.
    :param sn: The expected serial number.
    :type sn: str
    :param timeout: The read timeout.
    :type timeout: int
    :return: The next envelope.
    :rtype: Envelope
    """
    log.debug('searching for: sn=%s', sn)
    while True:
        envelope, ack = reader.next(timeout)
        if envelope:
            ack()
        else:
            return
        if sn == envelope.sn:
            log.debug('search found:\n%s', envelope)
            return envelope
        else:
            log.debug('search discarding:\n%s', envelope)


# --- model ------------------------------------------------------------------


class Options(object):
    """
    Provides a dict-like object that also provides
    (.) dot notation accessors.
    """

    def __init__(self, *things, **keywords):
        for thing in things:
            if isinstance(thing, dict):
                self.__dict__.update(thing)
                continue
            if isinstance(thing, Options):
                self.__dict__.update(thing.__dict__)
                continue
            raise ValueError(thing)
        self.__dict__.update(keywords)

    def __getattr__(self, name):
        return self.__dict__.get(name)

    def __getitem__(self, name):
        return self.__dict__[name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value

    def __iadd__(self, thing):
        if isinstance(thing, dict):
            self.__dict__.update(thing)
            return self
        if isinstance(thing, object):
            self.__dict__.update(thing.__dict__)
            return self
        raise ValueError(thing)

    def __len__(self):
        return len(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return str(self.__dict__)


class Envelope(Options):
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
        return json.dumps(d, sort_keys=True, indent=2)

