#!/usr/bin/env python3
#pylint: disable=c0111
from os import remove
from subprocess import check_call, CalledProcessError

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
