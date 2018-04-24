# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from six import with_metaclass

"""
Request tracker classes.
"""
import os

from threading import RLock

from gofer import Singleton, synchronized, NAME
from gofer.common import mkdir


class Tracker(with_metaclass(Singleton)):
    """
    Request tracker used to track information about
    active RMI requests.
    :ivar __all: All known requests by serial number.
    :type __all: dict
    :ivar __cancelled: Cancelled requests.
    :type __cancelled: Canceled
    :ivar __mutex: The object mutex.
    :type __mutex: RLock
    """

    def __init__(self):
        self.__all = dict()
        self.__cancelled = Canceled()
        self.__mutex = RLock()

    @synchronized
    def add(self, sn, locator):
        """
        Add a serial number (make known) for tracking.
        :param sn: An RMI serial number.
        :type sn: str
        :param locator:  The object used by find() to match
            on RMI requests.
        :type locator: object
        """
        self.__all[sn] = locator

    @synchronized
    def find(self, criteria):
        """
        Find serial numbers matching user defined (any) data.
        :param criteria: The object used to match RMI requests.
        :type criteria: gofer.rmi.criteria.Criteria
        :return: The list of matching serial numbers.
        :rtype: list
        """
        matched = []
        for sn, locator in self.__all.items():
            if criteria.match(locator):
                matched.append(sn)
        return matched

    @synchronized
    def cancel(self, sn):
        """
        Notify the tracker that an RMI request has been cancelled.
        :param sn: An RMI serial number.
        :type sn: str
        :return: The cancelled serial number (if not already cancelled).
        :rtype: str
        """
        if sn in self.__all:
            if sn not in self.__cancelled:
                self.__cancelled.add(sn)
                return sn
        else:
            raise Exception('serial number (%s), not-found' % sn)

    @synchronized
    def cancelled(self, sn):
        """
        Get whether an RMI request has been cancelled.
        :param sn: An RMI serial number.
        :type sn: str
        :return: True if cancelled.
        :rtype: bool
        """
        return sn in self.__cancelled

    @synchronized
    def remove(self, sn):
        """
        Discontinue tracking an RMI request.
        :param sn: An RMI serial number.
        :type sn: str
        """
        self.__all.pop(sn, 0)
        self.__cancelled.delete(sn)


class Canceled(object):
    """
    Persistent collection of canceled requests by serial number.
    :ivar collection: The set canceled requests (serial number).
    :type collection: set
    """

    PATH = '/var/lib/%s/messaging/canceled' % NAME

    def __init__(self):
        mkdir(Canceled.PATH)
        self.collection = set(os.listdir(Canceled.PATH))

    def add(self, sn):
        """
        Add a serial number.
        :param sn: A canceled request serial number.
        :rtype: str
        """
        self.collection.add(sn)
        with open(os.path.join(Canceled.PATH, sn), 'w+') as fp:
            fp.write(sn)

    def delete(self, sn):
        """
        Delete a serial number.
        :param sn: A canceled request serial number.
        :rtype: str
        """
        try:
            self.collection.remove(sn)
        except KeyError:
            pass
        try:
            os.unlink(os.path.join(Canceled.PATH, sn))
        except OSError:
            pass

    def __contains__(self, sn):
        return sn in self.collection
