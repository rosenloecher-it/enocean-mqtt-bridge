import os

import pathlib


class SetupTest:

    @classmethod
    def get_work_dir(cls):
        project_dir = cls.get_project_dir()
        out = os.path.join(project_dir, '__test__')
        return out

    @classmethod
    def ensure_work_dir(cls):
        work_dir = cls.get_work_dir()
        exists = os.path.exists(work_dir)
        is_dir = os.path.isdir(work_dir)

        if exists and not is_dir:
            raise NotADirectoryError(work_dir)
        if not exists:
            os.makedirs(work_dir)

        return work_dir

    @classmethod
    def ensure_clean_work_dir(cls):
        work_dir = cls.get_work_dir()
        exists = os.path.exists(work_dir)
        # is_dir = os.path.isdir(work_dir)

        if not exists:
            cls.ensure_work_dir()
        else:
            cls.clean_dir_recursively(work_dir)

        return work_dir

    @classmethod
    def clean_dir_recursively(cls, path_in):
        dirobj = pathlib.Path(path_in)
        if not dirobj.is_dir():
            return
        for item in dirobj.iterdir():
            if item.is_dir():
                cls.clean_dir_recursively(item)
                os.rmdir(item)
            else:
                item.unlink()

    @classmethod
    def get_project_dir(cls):
        file_path = os.path.dirname(__file__)
        # go up one time
        out = os.path.dirname(file_path)
        return out
