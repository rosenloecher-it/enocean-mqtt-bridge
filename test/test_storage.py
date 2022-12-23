import datetime
import os
import unittest

import pickle

from src.storage import Storage, StorageException
from test.setup_test import SetupTest


class TestStorage(unittest.TestCase):

    def test_roundtrip(self):
        work_dir = SetupTest.ensure_clean_work_dir()

        storage_path = os.path.join(work_dir, 'storage_test.yaml')
        self.assertFalse(os.path.exists(storage_path))

        p = Storage()
        p.set_file(storage_path)
        p.load()

        data1 = {"abc": 123, "456": "rr", 'list': [1, 2, 3, "str"]}
        p.set("data1", data1)
        tz = datetime.timezone(datetime.timedelta(seconds=3600))
        data2 = datetime.datetime(2018, 12, 3, 13, 7, 45, tzinfo=tz)
        p.set("data2", data2)
        data3 = 123
        p.set("data3", data3)

        p.save()
        self.assertTrue(os.path.exists(storage_path))

        p = Storage()
        p.set_file(storage_path)
        p.load()

        comp1 = p.get("data1")
        self.assertEqual(comp1, data1)
        comp2 = p.get("data2")
        self.assertEqual(comp2, data2)
        comp3 = p.get("data3")
        self.assertEqual(comp3, data3)

    def test_read_not_exists(self):
        work_dir = SetupTest.ensure_clean_work_dir()
        storage_path = os.path.join(work_dir, 'file_must_not_exists.yaml')
        self.assertFalse(os.path.exists(storage_path))

        p = Storage()
        p.set_file(storage_path)

        p.load()

    def test_error_write_permission(self):
        path = "/usr/bin/not_allowed_to_write_into"
        self.assertFalse(os.path.exists(path))

        p = Storage()
        p.set_file(path)
        p.load()

        data1 = 123
        p.set("data1", data1)

        with self.assertRaises(StorageException):
            p.save()

        self.assertFalse(os.path.exists(path))

    def test_error_read_wrong_format(self):
        work_dir = SetupTest.ensure_clean_work_dir()
        storage_path = os.path.join(work_dir, 'error_wrong_format.yaml')
        self.assertFalse(os.path.exists(storage_path))

        byte_data = [120, 3, 255, 0, 100]
        with open(storage_path, "wb") as stream:
            pickle.dump(byte_data, stream)

        self.assertTrue(os.path.isfile(storage_path))

        p = Storage()
        p.set_file(storage_path)

        with self.assertRaises(StorageException):
            p.load()
