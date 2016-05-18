import os
import tarfile


def touch(fname):
    if os.path.exists(fname):
        os.utime(fname, None)
    else:
        open(fname, 'a').close()


def extract_tar(tarbal, dest):
    if not tarfile.is_tarfile(tarbal):
        raise ValueError('%s is not a tarbal')

    arch = tarfile.open(tarbal)
    arch.extractall(dest)
