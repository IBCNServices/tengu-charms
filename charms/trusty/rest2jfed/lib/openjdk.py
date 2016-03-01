#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301

from charmhelpers.core import hookenv

import charms.apt #pylint: disable=e0611,e0401


def installopenjdk():
    hookenv.log('Installing OpenJDK')
    conf = hookenv.config()
    install_type = conf['install-type']
    java_major = conf['java-major']
    charms.apt.queue_install(['openjdk-%s-jre-headless' % java_major]) # pylint: disable=e1101
    if install_type == 'full':
        charms.apt.queue_install(['openjdk-%s-jdk' % java_major])# pylint: disable=e1101
        # return 'openjdk-%s-jdk' % java_major
    # TODO remove when reactive fixed
    charms.apt.install_queued()# pylint: disable=e1101
    return 'openjdk-%s-jre-headless' % java_major
