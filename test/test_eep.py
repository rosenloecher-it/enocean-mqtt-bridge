import unittest

from src.common.eep import Eep


class TestEep(unittest.TestCase):

    def setUp(self):
        self.eep = Eep(
            rorg=0xa5,
            func=0x38,
            type=0x08,
            direction=None,
            command=0x02
        )

    def test_to_string(self):
        self.assertEqual(str(self.eep), "a5-38-08")
        self.assertEqual(repr(self.eep), "Eep(a5-38-08)")

    def test_equals(self):
        clone = self.eep.clone()

        self.assertTrue(self.eep == self.eep)
        self.assertTrue(self.eep == clone)

        clone = self.eep.clone()
        clone.rorg = clone.rorg + 1
        self.assertFalse(self.eep == clone)

        clone = self.eep.clone()
        clone.func = clone.func + 1
        self.assertFalse(self.eep == clone)

        clone = self.eep.clone()
        clone.type = clone.type + 1
        self.assertFalse(self.eep == clone)

        clone = self.eep.clone()
        clone.direction = 1
        self.assertFalse(self.eep == clone)

        clone = self.eep.clone()
        clone.command = None
        self.assertFalse(self.eep == clone)
