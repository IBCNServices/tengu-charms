#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import os
import re
import glob
import shutil
import tarfile
import subprocess

from jujubigdata import utils
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir


def installoracle():
    hookenv.log('Installing Oracle JDK')
    filesdir = '{}/files/'.format(charm_dir())
    conf = hookenv.config()
    (tarname, dirname) = get_java_paths(filesdir, conf['install-type'], conf['java-major'])
    destdir = "/opt/java/{}".format(dirname)
    if not os.path.isdir(destdir):
        tfile = tarfile.open(
            '{}/files/{}'.format(charm_dir(), tarname), 'r')
        # Important to note that the following extraction is
        # UNSAFE since .tar.gz archive could contain
        # relative path like ../../ and overwrite other dirs
        extractdir = '{}/{}'.format(filesdir, dirname)
        tfile.extractall(filesdir)
        mergecopytree(extractdir, destdir)
        # Set defaults
        subprocess.check_output(['update-alternatives', '--install', '/usr/bin/java', 'java', '{}/jre/bin/java'.format(destdir), '2000'])
        subprocess.check_output(['update-alternatives', '--install', '/usr/bin/javac', 'javac', '{}/bin/javac'.format(destdir), '2000'])
        # set env vars
        with utils.environment_edit_in_place('/etc/environment') as env:
            # ensure that correct java is used
            env['JAVA_HOME'] = destdir
            env['J2SDKDIR'] = destdir
            env['J2REDIR'] = '{}/jre'.format(destdir)
            env['DERBY_HOME'] = '{}/db'.format(destdir)
            if destdir not in env['PATH']:
                env['PATH'] = ':'.join([
                    '{}/bin'.format(env['JAVA_HOME']),
                    '{}/bin'.format(env['J2REDIR']),
                    '{}/bin'.format(env['DERBY_HOME']),
                    env['PATH'],
                ])


def get_java_paths(filesdir, install_type, java_major):
    if install_type == 'jre':
        tarstr = 'server-jre-{}u{}-linux-x64.tar.gz'
    else:
        tarstr = 'jdk-{}u{}-linux-x64.tar.gz'
    filenames = glob.glob(filesdir + '/' + tarstr.format(java_major, '*'))
    p = re.compile(r'-{}u([0-9]+)-'.format(java_major))
    versions = [p.search(filename).group(1) for filename in filenames]
    java_minor = max(versions)
    tarname = tarstr.format(java_major, java_minor)
    dirname = 'jdk1.{}.0_{}'.format(java_major, java_minor)
    return (tarname, dirname)


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
