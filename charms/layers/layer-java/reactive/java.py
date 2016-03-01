#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import subprocess
import os

from charmhelpers.core import hookenv
from charms.reactive import when, when_not, set_state

import openjdk
import oracle

java_install = ""


@when_not('java.installed')
def install():
    global java_install
    conf = hookenv.config()
    hookenv.log("Installing dependencies")
    try:
        subprocess.check_output(['sudo', 'apt-get', 'update'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception)
        exit(1)
    if conf['java-flavor'] == 'openjdk':
        java_install = openjdk.installopenjdk()
    elif conf['java-flavor'] == 'oracle':
        java_install = oracle.installoracle()
    else:
        java_install = openjdk.installopenjdk()
    # TODO change to reactive
    configure()


# @when('apt.installed.%s' % java_install)
# @when_not('java.installed')
def configure():
    hookenv.log("Configuring Java")
    proc = subprocess.Popen(['readlink', '-f /usr/bin/java | sed "s:/bin/java::"'], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    os.environ['JAVA_HOME'] = out
    set_state('java.installed')
