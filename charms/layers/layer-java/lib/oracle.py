#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import subprocess

from charmhelpers.core import hookenv

import charms.apt


def installoracle():
    hookenv.log('Installing Oracle JDK')
    conf = hookenv.config()
    java_major = conf['java-major']
    charms.apt.queue_install(['software-properties-common', 'python-software-properties', 'debconf-utils'])
    charms.apt.install_queued()
    subprocess.check_output(['sudo', 'apt-add-repository', 'ppa:webupd8team/java', '-y'])
    subprocess.check_output(['sudo', 'apt-get', 'update'])
    # Set license selected and seen
    subprocess.check_output(['echo "oracle-java%s-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections' % java_major])
    subprocess.check_output(['echo "oracle-java%s-installer shared/accepted-oracle-license-v1-1 seen true" | sudo debconf-set-selections' % java_major])
    # subprocess.check_output(['echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections'])
    # subprocess.check_output(['echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections'])
    charms.apt.queue_install(['oracle-java%s-installer' % java_major])
    # TODO remove when reactive fixed
    charms.apt.install_queued()
    return 'oracle-java%s-installer' % java_major
