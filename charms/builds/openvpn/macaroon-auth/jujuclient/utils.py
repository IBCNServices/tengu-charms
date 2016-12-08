import logging
import subprocess

log = logging.getLogger(__name__)

_juju_major_version = None


def get_juju_major_version():
    global _juju_major_version
    if _juju_major_version is None:
        _juju_major_version = int(subprocess.check_output(
            ["juju", "--version"]).split(b'.')[0])
    return _juju_major_version


def check_output(*args, **kw):
    try:
        if 'stderr' not in kw:
            kw['stderr'] = subprocess.STDOUT
        output = subprocess.check_output(*args, **kw)
    except subprocess.CalledProcessError as e:
        err_msg = "Command ({}) Output:\n\n {}\n".format(
            " ".join(args[0]), e.output)
        log.error(err_msg)
        raise
    return output
