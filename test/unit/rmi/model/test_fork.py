from unittest import TestCase

from mock import Mock

from gofer.rmi.model.fork import Call


class TestCall(TestCase):

    def test_call(self):
        method = Mock()
        Call(method)
