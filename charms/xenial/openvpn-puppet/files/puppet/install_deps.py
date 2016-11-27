#!/usr/bin/env python3
#pylint: disable=c0111
import os
from os import remove
import shutil
import tarfile
from subprocess import check_call, CalledProcessError

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

try:
    check_call(['puppet'])
except CalledProcessError:
    check_call(['wget', 'https://apt.puppetlabs.com/puppetlabs-release-pc1-xenial.deb'])
    check_call(['sudo', 'dpkg', '-i', 'puppetlabs-release-pc1-xenial.deb'])
    remove('puppetlabs-release-pc1-xenial.deb')
    check_call(['sudo', 'apt-get', 'update'])
    check_call(['sudo', 'apt-get', 'install', '-y', 'puppet'])

try:
    check_call(['librarian-puppet'])
except CalledProcessError:
    check_call(['sudo', 'gem', 'install', 'librarian-puppet'])

check_call(['librarian-puppet', 'install', '--verbose'])
make_tarfile('modules.tgz', 'modules')
shutil.rmtree('modules')
shutil.rmtree('.tmp')
