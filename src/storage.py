import os
import yaml


CONFKEY_STORAGE_FILE = "storage_file"
CONFKEY_STORAGE_MAX_AGE_SECS = "storage_max_age_secs"  # former: "restore_last_max_diff"


class StorageException(Exception):
    pass


class Storage:

    def __init__(self):
        self._file = None
        self._data = {}

    def set_file(self, file):
        self._file = file

    def empty(self):
        self._data = {}

    def load(self):
        try:
            if self._file is not None and os.path.isfile(self._file):
                with open(self._file, 'r') as stream:
                    self._data = yaml.unsafe_load(stream)
            else:
                self.empty()
        except (PermissionError, ValueError) as ex:
            raise StorageException(ex)

    def save(self):
        if self._file is not None:
            try:
                # backup and write to a new file to avoid flashing the same sdcards bits again and again?
                with open(self._file, 'w') as stream:
                    yaml.dump(self._data, stream, default_flow_style=False)
            except PermissionError as ex:
                raise StorageException(ex)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)
