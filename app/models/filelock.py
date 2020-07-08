from time import time, sleep
import os

"""
Code inspired by: https://github.com/dmfrey/FileLock

Creates an exclusive file lock by creating a dummy file called <filename>.lock.

Usage:
# Reading
with FileLock("<filepath>", "r") as f:
    text = f.read()

# Writing
with FileLock("<filepath>", "w") as f:
    f.write("something")
"""


class FileLockException(Exception):
    pass


class FileLock:
    def __init__(self, target_file_path, flags, *, max_timeout=5, delay=0.05):
        self.target_file_path = target_file_path
        self.flags = flags
        self.max_timeout = max_timeout
        self.delay = delay

        self.lock_file_path = f"{target_file_path}.lock"
        self.lock_file_descriptor = None
        self.target_file = None
        self.locked = False

    def acquire(self):
        start_time = time()
        while not self.locked:
            try:
                self.lock_file_descriptor = os.open(
                    self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_RDWR
                )
                try:
                    self.target_file = open(self.target_file_path, self.flags)
                    self.locked = True
                except FileNotFoundError:
                    # Unable to access target file, rollback lock file creation
                    os.close(self.lock_file_descriptor)
                    os.unlink(self.lock_file_path)
                    raise
            except FileExistsError:
                # Lock file already exists
                if start_time + self.max_timeout < time():
                    raise FileLockException
                sleep(self.delay)

    def release(self):
        if self.locked:
            self.target_file.close()
            os.close(self.lock_file_descriptor)
            os.unlink(self.lock_file_path)
            self.locked = False

    def __enter__(self):
        self.acquire()
        return self.target_file

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        self.release()
