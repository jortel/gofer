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


class InvalidOperator(Exception):
    pass


class Criteria:
    """
    The criteria used to match on an RMI locator.
    """

    def __init__(self, criteria):
        """
        @param criteria: The data used for matching.
        @type criteria: object
        """
        self.criteria = criteria

    def match(self, locator):
        """
        Match on the specified criteria.
        @param locator: RMI request locator information.
        @type locator: object
        @return: True on match.
        @rtype: bool
        """
        raise NotImplementedError()


class Equal(Criteria):

    def match(self, locator):
        return locator == self.criteria


class NotEqual(Criteria):

    def match(self, locator):
        return locator != self.criteria


class Greater(Criteria):

    def match(self, locator):
        return locator > self.criteria


class Less(Criteria):

    def match(self, locator):
        return locator < self.criteria


class In(Criteria):

    def match(self, locator):
        return locator in self.criteria


class And(Criteria):

    def match(self, locator):
        left, right = self.criteria
        return left.match(locator) and right.match(locator)


class Or(Criteria):

    def match(self, locator):
        left, right = self.criteria
        return left.match(locator) or right.match(locator)


class Builder:
    """
    Build a criteria object graph based on dictionary representations.
    These representations can be nested.
    Examples:
      {'eq':10}
      {'neq':10}
      {'in':[1,2]}
      {'gt':10}
      {'lt':10}
      {'and':({'gt':1},{'lt':10})}
      {'or':({'eq':10},{'in':[1,2]})}
      {'or':({'eq':10},{'or':({'eq':1},{'eq':2})}
    """

    METHODS = {
        'eq':Equal,
        'neq':NotEqual,
        'in':In,
        'gt':Greater,
        'lt':Less,
        'and':And,
        'or':Or,
    }

    def build(self, criteria):
        """
        Build a L{Criteria} object based on the specified
        dict representation.
        @param criteria: The criteria to build.
        @type criteria: dict
        @rtype: L{Criteria}
        @raise Exception, on invalid criteria.
        """
        for k, v in criteria.items():
            if self._criteria(v):
                v = self._resolve(v)
            m = self.METHODS.get(k)
            if m:
                return m(self._resolve(v))
            else:
                raise InvalidOperator, '%s not supported' % k

    def _resolve(self, object):
        if self._criteria(object):
            return self.build(object)
        if isinstance(object, (list,tuple)) and len(object) == 2:
            left, right = object
            if self._criteria(left) and self._criteria(right):
                left = self.build(left)
                right = self.build(right)
                return (left, right)
        return object

    def _criteria(self, object):
        if isinstance(object, dict):
            for k in self.METHODS:
                if k in object:
                    return True
        return False