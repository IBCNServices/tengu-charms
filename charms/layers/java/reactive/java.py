#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import subprocess

from charmhelpers.core import hookenv
from charms.reactive import when_not, set_state

import openjdk
import oracle


@when_not('java.installed')
def install():
    conf = hookenv.config()
    hookenv.log("Installing dependencies")
    try:
        subprocess.check_output(['sudo', 'apt-get', 'update'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception)
        exit(1)
    if conf['java-flavor'] == 'openjdk':
        openjdk.installopenjdk()
    elif conf['java-flavor'] == 'oracle':
        oracle.installoracle()
    else:
        openjdk.installopenjdk()
    set_state('java.installed')
