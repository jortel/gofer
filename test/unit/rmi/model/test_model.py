from unittest import TestCase

from gofer.rmi.model import ALL, valid_model


class TestModel(TestCase):

    def test_valid_model(self):
        # valid
        for model in ALL:
            self.assertTrue(valid_model(model))
        # invalid
        self.assertRaises(ValueError, valid_model, 1234)
