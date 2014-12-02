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

from unittest import TestCase

from gofer.agent.deplist import DepList


class TestDepList(TestCase):

    def test_init(self):
        dl = DepList()
        self.assertEqual(dl.unsorted, [])
        self.assertEqual(dl.index, {})
        self.assertEqual(dl.stack, [])
        self.assertEqual(dl.pushed, set())
        self.assertEqual(dl.sorted, None)

    def test_add(self):
        items = [(1, 2), (3, 4)]
        dl = DepList()
        dl.add(*items)
        self.assertEqual(dl.unsorted, items)
        self.assertEqual(dl.index, {1: (1, 2), 3: (3, 4)})

    def test_sort(self):
        a = ('a', ('x',))
        b = ('b', ('a',))
        c = ('c', ('a', 'b'))
        d = ('d', ('c',))
        e = ('e', ('d', 'a'))
        f = ('f', ('e', 'c', 'd', 'a'))
        x = ('x', ())
        g = ('g', ('G',))
        dl = DepList()
        dl.add(c, e, d, b, f, a, x, g)
        self.assertEqual(
            dl.sort(),
            [
                ('x', ()),
                ('a', ('x',)),
                ('b', ('a',)),
                ('c', ('a', 'b')),
                ('d', ('c',)),
                ('e', ('d', 'a')),
                ('f', ('e', 'c', 'd', 'a')),
                ('g', ('G',))
            ])

    def test_top(self):
        dl = DepList()
        dl.stack = [1, 2, 3]
        self.assertEqual(dl.top(), dl.stack[-1])

    def test_push(self):
        item = ('a', ('b',))
        dl = DepList()
        dl.push(item)
        self.assertEqual(len(dl.stack), 1)
        self.assertEqual(dl.pushed, {item})
        # 2nd push skipped
        dl.push(item)
        self.assertEqual(len(dl.stack), 1)
        self.assertEqual(dl.pushed, {item})

    def test_pop(self):
        item = ('a', ('b',))
        dl = DepList()
        dl.push(item)
        # has
        popped = dl.pop()
        self.assertEqual(popped, item)
        # empty
        popped = dl.pop()
        self.assertEqual(popped, None)
