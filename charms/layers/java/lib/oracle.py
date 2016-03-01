#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import os
import shutil
import tarfile
import subprocess

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir


def installoracle():
    hookenv.log('Installing Oracle JDK')
    java_major = '8'
    java_minor = '73'
    tarname = 'server-jre-{}u{}-linux-x64.tar.gz'.format(java_major, java_minor)
    dirname = 'jdk1.{}.0_{}'.format(java_major, java_minor)
    if not os.path.isdir('/opt/java/jre1.8.0_45'):
        tfile = tarfile.open(
            '{}/files/{}'.format(charm_dir(), tarname), 'r')
        # Important to note that the following extraction is
        # UNSAFE since .tar.gz archive could contain
        # relative path like ../../ and overwrite other dirs
        filesdir = '{}/files/'.format(charm_dir())
        extractdir = '{}/{}'.format(filesdir, dirname)
        destdir = "/opt/java/{}".format(dirname)
        tfile.extractall(filesdir)
        mergecopytree(extractdir, destdir)
        # Set defaults
        subprocess.check_output(['update-alternatives', '--install', '/usr/bin/java', 'java', '{}/jre/bin/java'.format(destdir), '2000'])
        subprocess.check_output(['update-alternatives', '--install', '/usr/bin/javac', 'javac', '{}/bin/javac'.format(destdir), '2000'])
        # set env vars
        env_vars = [
            'J2SDKDIR={}'.format(destdir),
            'J2REDIR={}/jre'.format(destdir),
            'PATH=$PATH:{0}/bin:{0}/db/bin:{0}/jre/bin'.format(destdir),
            'JAVA_HOME={}'.format(destdir),
            'DERBY_HOME={}/db'.format(destdir),
        ]
        for line in env_vars:
            add_line_to_file(line, '/etc/environment')


#import charms.apt #pylint: disable=E1101
# def installoracle_desktop():
#     hookenv.log('Installing Oracle JDK')
#     conf = hookenv.config()
#     java_major = conf['java-major']
#     charms.apt.queue_install(['software-properties-common', 'python-software-properties', 'debconf-utils'])#pylint: disable=E1101
#     charms.apt.install_queued()#pylint: disable=E1101
#     subprocess.check_output(['sudo', 'apt-add-repository', 'ppa:webupd8team/java', '-y'])
#     subprocess.check_output(['sudo', 'apt-get', 'update'])
#     # Set license selected and seen
#     subprocess.check_output(['echo "oracle-java%s-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections' % java_major])
#     subprocess.check_output(['echo "oracle-java%s-installer shared/accepted-oracle-license-v1-1 seen true" | sudo debconf-set-selections' % java_major])
#     # subprocess.check_output(['echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections'])
#     # subprocess.check_output(['echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections'])
#     charms.apt.queue_install(['oracle-java%s-installer' % java_major])#pylint: disable=E1101
#     # TODO remove when reactive fixed
#     charms.apt.install_queued()#pylint: disable=E1101
#     return 'oracle-java%s-installer' % java_major
#
#


def mergecopytree(src, dst, symlinks=False, ignore=None):
    """"Recursive copy src to dst, mergecopy directory if dst exists.
    OVERWRITES EXISTING FILES!!"""
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if symlinks and os.path.islink(src_item):
            if os.path.lexists(dst_item):
                os.remove(dst_item)
            os.symlink(os.readlink(src_item), dst_item)
        elif os.path.isdir(src_item):
            mergecopytree(src_item, dst_item, symlinks, ignore)
        else:
            shutil.copy2(src_item, dst_item)


def add_line_to_file(line, filepath):
    """appends line to file if not present"""
    filepath = os.path.realpath(filepath)
    if not os.path.isdir(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    found = False
    if os.path.isfile(filepath):
        with open(filepath, 'r+') as myfile:
            lst = myfile.readlines()
        for existingline in lst:
            if line in existingline:
                print("line already present")
                found = True
    if not found:
        myfile = open(filepath, 'a+')
        myfile.write(line+"\n")
        myfile.close()
