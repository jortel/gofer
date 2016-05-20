from unittest import TestCase

from mock import Mock

from gofer.rmi.model.direct import Call


class TestCall(TestCase):

    def test_call(self):
        method = Mock()
        args = [1, 2]
        kwargs = {'A': 1}

        # test
        model = Call(method, *args, **kwargs)
        retval = model()

        # validation
        method.assert_called_once_with(*args, **kwargs)
        self.assertEqual(retval, method.return_value)
