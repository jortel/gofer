from unittest import TestCase

from mock import Mock

from gofer.rmi.mode.direct import Direct


class TestDirect(TestCase):

    def test_call(self):
        inst = Mock()
        method = inst.bark
        passed = ([1, 2], {'A': 1})

        # test
        mode = Direct(inst, method, passed)
        retval = mode()

        # validation
        method.assert_called_once_with(*passed[0], **passed[1])
        self.assertEqual(retval, method.return_value)
