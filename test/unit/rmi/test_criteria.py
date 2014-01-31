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

from unittest import TestCase
from gofer.rmi.criteria import *


class TestCriteria(TestCase):

    def test_match(self):
        match = Match({'id': 44, 'age': 88})
        self.assertTrue(match({'id': 44}))
        self.assertTrue(match({'id': 44, 'age': 88}))
        self.assertTrue(match({'id': 44, 'age': 88}))
        self.assertTrue(match({'age': 88}))
        self.assertFalse(match({'id': 88}))
        self.assertFalse(match({'id': 14, 'age': 18}))
        self.assertFalse(match(88))
        self.assertFalse(match(88))
        self.assertFalse(match({}))
        match = Match(88)
        self.assertFalse(match({'id': 44}))
        self.assertFalse(match({'id': 44, 'age': 88}))
        self.assertFalse(match({'id': 44, 'age': 88}))
        self.assertFalse(match({'age': 88}))

    def test_eq(self):
        eq = Equal(1)
        self.assertTrue(eq.match(1))
        self.assertFalse(eq.match(2))

    def test_neq(self):
        neq = NotEqual(1)
        self.assertTrue(neq.match(2))
        self.assertFalse(neq.match(1))

    def test_gt(self):
        gt = Greater(1)
        self.assertTrue(gt.match(2))
        self.assertFalse(gt.match(1))

    def test_lt(self):
        lt = Less(2)
        self.assertTrue(lt.match(1))
        self.assertFalse(lt.match(2))

    def test_in(self):
        _in = In([1,2])
        self.assertTrue(_in.match(1))
        self.assertFalse(_in.match(3))

    def test_and(self):
        _and = And((Greater(1), Less(3)))
        self.assertTrue(_and.match(2))
        self.assertFalse(_and.match(1))
        self.assertFalse(_and.match(3))

    def test_or(self):
        _or = Or((Equal(1), Equal(3)))
        self.assertTrue(_or.match(1))
        self.assertTrue(_or.match(3))
        self.assertFalse(_or.match(2))


class TestBuilder(TestCase):

    def test_match(self):
        b = Builder()
        match = b.build({'match': {'id': 44, 'age': 88}})
        self.assertTrue(match({'id': 44}))
        self.assertTrue(match({'id': 44, 'age': 88}))
        self.assertTrue(match({'id': 44, 'age': 88}))
        self.assertTrue(match({'age': 88}))
        self.assertFalse(match({'id': 88}))
        self.assertFalse(match({'id': 14, 'age': 18}))
        self.assertFalse(match(88))
        self.assertFalse(match(88))
        self.assertFalse(match({}))
        match = b.build({'match': 88})
        self.assertFalse(match({'id': 44}))
        self.assertFalse(match({'id': 44, 'age': 88}))
        self.assertFalse(match({'id': 44, 'age': 88}))
        self.assertFalse(match({'age': 88}))

    def test_eq(self):
        b = Builder()
        eq = b.build({'eq':1})
        self.assertTrue(eq.match(1))
        self.assertFalse(eq.match(2))

    def test_neq(self):
        b = Builder()
        neq = b.build({'neq':1})
        self.assertTrue(neq.match(2))
        self.assertFalse(neq.match(1))

    def test_gt(self):
        b = Builder()
        gt = b.build({'gt':1})
        self.assertTrue(gt.match(2))
        self.assertFalse(gt.match(1))

    def test_lt(self):
        b = Builder()
        lt = b.build({'lt':2})
        self.assertTrue(lt.match(1))
        self.assertFalse(lt.match(2))

    def test_in(self):
        b = Builder()
        _in = b.build({'in':[1,2]})
        self.assertTrue(_in.match(1))
        self.assertFalse(_in.match(3))

    def test_and(self):
        b = Builder()
        q = {'and':({'gt':1}, {'lt':3})}
        _and = b.build(q)
        self.assertTrue(_and.match(2))
        self.assertFalse(_and.match(1))
        self.assertFalse(_and.match(3))

    def test_or(self):
        b = Builder()
        q = {'or':({'eq':1}, {'eq':3})}
        _or = b.build(q)
        self.assertTrue(_or.match(1))
        self.assertTrue(_or.match(3))
        self.assertFalse(_or.match(2))

    def test_nested(self):
        b = Builder()
        q = {
            'or':[
                {'eq':10},
                {'or':[{'eq':1},{'eq':2}]}
            ]
        }
        _or = b.build(q)
        self.assertTrue(_or.match(10))
        self.assertTrue(_or.match(1))
        self.assertTrue(_or.match(2))
        self.assertFalse(_or.match(3))

    def test_unsupported(self):
        b = Builder()
        q = {'xx':1}
        self.assertRaises(InvalidOperator, b.build, q)
