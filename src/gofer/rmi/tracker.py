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

"""
Request tracker classes.
"""

from threading import RLock

from gofer import Singleton, synchronized


class Tracker:
    """
    Request tracker used to track information about
    active RMI requests.
    :ivar __all: All known requests by serial number.
    :type __all: set
    :ivar __cancelled: Cancelled requests.
    :type __cancelled: set
    :ivar __mutex: The object mutex.
    :type __mutex: RLock
    """

    __metaclass__ = Singleton

    def __init__(self):
        self.__all = dict()
        self.__cancelled = set()
        self.__mutex = RLock()

    @synchronized
    def add(self, sn, locator):
        """
        Add a serial number (make know) for tracking.
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
            raise Exception, 'serial number (%s), not-found' % sn

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
        self.__all.pop(sn)
        if sn in self.__cancelled:
            self.__cancelled.remove(sn)