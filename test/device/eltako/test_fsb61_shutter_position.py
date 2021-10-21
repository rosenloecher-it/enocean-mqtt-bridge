import unittest

from src.device.eltako.fsb61_eep import Fsb61Status, Fsb61StatusType
from src.device.eltako.fsb61_shutter_position import Fsb61ShutterPosition, Fsb61ShutterState


class TestFsb61ShutterPosition(unittest.TestCase):

    def setUp(self):
        self.sp = Fsb61ShutterPosition("test")
        self.sp.time_down_driving = 18.0
        self.sp.time_down_rolling = 4.0
        self.sp.time_up_driving = 22.0
        self.sp.time_up_rolling = 6.0

    def test_validate_value(self):
        self.assertFalse(Fsb61ShutterPosition.validate_value(None))
        self.assertFalse(Fsb61ShutterPosition.validate_value(-1))
        self.assertFalse(Fsb61ShutterPosition.validate_value(101))

        self.assertTrue(Fsb61ShutterPosition.validate_value(0))
        self.assertTrue(Fsb61ShutterPosition.validate_value(0.0))
        self.assertTrue(Fsb61ShutterPosition.validate_value(49))
        self.assertTrue(Fsb61ShutterPosition.validate_value(100))
        self.assertTrue(Fsb61ShutterPosition.validate_value(100.0))

    def test_calibrate(self):
        self.assertEqual(self.sp.state, Fsb61ShutterState.NOT_CALIBRATED)
        self.assertEqual(self.sp.value, None)

        change = Fsb61Status(type=Fsb61StatusType.CLOSED, time=8)
        self.sp.update(change)

        self.assertEqual(self.sp.state, Fsb61ShutterState.NOT_CALIBRATED)
        self.assertEqual(self.sp.value, None)

        change = Fsb61Status(type=Fsb61StatusType.CLOSED, time=14)
        self.sp.update(change)

        self.assertEqual(self.sp.state, Fsb61ShutterState.READY)
        self.assertEqual(self.sp.value, 100)

    def test_seek_up(self):

        self.sp.value = 100
        change = Fsb61Status(type=Fsb61StatusType.OPENED, time=self.sp.time_up_rolling)
        self.sp.update(change)
        self.assertEqual(self.sp.value, Fsb61ShutterPosition.ROLLING)

        self.sp.value = 100
        change = Fsb61Status(type=Fsb61StatusType.OPENED, time=self.sp.time_up_rolling + self.sp.time_up_driving / 2)
        self.sp.update(change)
        self.assertEqual(self.sp.value, 45)

        self.sp.value = 100
        change = Fsb61Status(type=Fsb61StatusType.OPENED, time=self.sp.time_up_rolling / 2)
        self.sp.update(change)
        self.assertEqual(self.sp.value, 95)

    def test_seek_down(self):

        self.sp.value = 0
        change = Fsb61Status(type=Fsb61StatusType.CLOSED, time=self.sp.time_down_driving + self.sp.time_down_rolling / 2)
        self.sp.update(change)
        self.assertEqual(self.sp.value, 95)

        self.sp.value = 0
        change = Fsb61Status(type=Fsb61StatusType.CLOSED, time=self.sp.time_down_driving / 2)
        self.sp.update(change)
        self.assertEqual(self.sp.value, 45)

        self.sp.value = 0
        change = Fsb61Status(type=Fsb61StatusType.CLOSED, time=self.sp.time_down_driving)
        self.sp.update(change)
        self.assertEqual(self.sp.value, 90.0)

    def test_calc_seek_time(self):
        drive_pos_middle = Fsb61ShutterPosition.ROLLING / 2
        roll_pos_start = Fsb61ShutterPosition.ROLLING
        roll_pos_middle = roll_pos_start + (100 - roll_pos_start) / 2

        time = self.sp.calc_seek_time(drive_pos_middle, roll_pos_middle)
        self.assertEqual(time, self.sp.time_down_driving / 2 + self.sp.time_down_rolling / 2)

        time = self.sp.calc_seek_time(roll_pos_middle, drive_pos_middle)
        self.assertEqual(time, self.sp.time_up_driving / 2 + self.sp.time_up_rolling / 2)

        time = self.sp.calc_seek_time(roll_pos_start, roll_pos_middle)
        self.assertEqual(time, self.sp.time_down_rolling / 2)

        time = self.sp.calc_seek_time(roll_pos_middle, roll_pos_start)
        self.assertEqual(time, self.sp.time_up_rolling / 2)

        time = self.sp.calc_seek_time(roll_pos_start, drive_pos_middle)
        self.assertEqual(time, self.sp.time_up_driving / 2)

        time = self.sp.calc_seek_time(drive_pos_middle, roll_pos_start)
        self.assertEqual(time, self.sp.time_down_driving / 2)

        time = self.sp.calc_seek_time(100, 0)
        self.assertEqual(time, self.sp.time_up_driving + self.sp.time_up_rolling)

        time = self.sp.calc_seek_time(0, 100)
        self.assertEqual(time, self.sp.time_down_driving + self.sp.time_down_rolling)
