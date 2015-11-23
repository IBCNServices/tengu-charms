# pylint: disable=c0111,c0103,c0301
def pre_install():
    """
    Do any setup required before the install hook.
    """
    install_charmhelpers()


def install_charmhelpers():
    import subprocess
    """
    Install the charmhelpers library, if not present.
    """
    try:
        import charmhelpers  # pylint: disable=W0612
    except ImportError:
        subprocess.check_call(['apt-get', 'install', '-y', 'python-pip', 'python-dev'])
        subprocess.check_call(['pip', 'install', 'charmhelpers'])
    try:
        import netifaces  # pylint: disable=W0612
    except ImportError:
        subprocess.check_call(['apt-get', 'install', '-y', 'python-pip', 'python-dev'])
        subprocess.check_call(['pip', 'install', 'netifaces'])
    try:
        import ipaddress  # pylint: disable=W0612
    except ImportError:
        subprocess.check_call(['apt-get', 'install', '-y', 'python-pip', 'python-dev'])
        subprocess.check_call(['pip', 'install', 'ipaddress'])
