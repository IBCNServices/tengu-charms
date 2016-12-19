#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301



import charms.apt #pylint: disable=e0611,e0401
from charmhelpers.core import hookenv

from jujubigdata import utils


def installopenjdk():
    hookenv.log('Installing OpenJDK')
    conf = hookenv.config()
    install_type = conf['install-type']
    java_major = conf['java-major']
    #openjdk 8 is not included in ubuntu repos
    if java_major == '8':
        charms.apt.add_source('ppa:openjdk-r/ppa')
    charms.apt.queue_install(['openjdk-%s-jre-headless' % java_major]) # pylint: disable=e1101
    if install_type == 'full':
        charms.apt.queue_install(['openjdk-%s-jdk' % java_major])# pylint: disable=e1101
        # return 'openjdk-%s-jdk' % java_major
    #TODO remove when reactive fixed
    return 'openjdk-%s-jre-headless' % java_major


def setjavahome():
    with utils.environment_edit_in_place('/etc/environment') as env:
        env['JAVA_HOME'] = '/usr/lib/jvm/java-1.%s.0-openjdk-amd64/' % clean_java_major()


# Cleaning user input before writing into .bashrc
def clean_java_major():
    try:
        value = int(hookenv.config()['java-major'][0])
    except ValueError:
        value = 8
    return value
