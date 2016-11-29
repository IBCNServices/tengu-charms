#!/usr/bin/python3
# pylint: disable=C0111,c0103,r0902
# Copyright (c) 2016, James Beedy <jamesbeedy@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import json
import errno
import tarfile
from subprocess import check_call, check_output
from distutils.dir_util import copy_tree

import charms.apt
from charms import layer
from charmhelpers.core import hookenv
from charmhelpers.core.host import lsb_release



config = hookenv.config()

class PuppetException(Exception):
    pass

class Puppet:
    def __init__(self):
        self.options = layer.options('puppet-base')
        self.puppet_pkg = self.options.get('puppet-srvc')
        self.puppet_base_url = 'http://apt.puppetlabs.com'
        self.puppet_gpg_key = config['puppet-gpg-key']
        self.puppet_exe = '/opt/puppetlabs/bin/puppet'
        self.facter_exe = '/opt/puppetlabs/bin/facter'
        self.puppet_conf_dir = '/etc/puppetlabs/puppet'
        self.modules_dir = '/etc/puppetlabs/code/modules/'
        self.puppet_apt_src = \
            'deb %s %s PC1' % (self.puppet_base_url,
                               lsb_release()['DISTRIB_CODENAME'])
        # Determine puppet apt package
        if self.puppet_pkg == 'master':
            self.puppet_apt_pkg = 'puppetserver'
            self.puppet_srvc = self.puppet_apt_pkg
        elif self.puppet_pkg == 'agent':
            self.puppet_apt_pkg = 'puppet-agent'
            self.puppet_srvc = 'puppet'
        elif self.puppet_pkg == 'db':
            self.puppet_apt_pkg = 'puppetdb'
            self.puppet_srvc = self.puppet_apt_pkg
        elif self.puppet_pkg == 'ca':
            self.puppet_apt_pkg = 'puppetserver'
            self.puppet_srvc = self.puppet_apt_pkg
        elif self.puppet_pkg == 'standalone':
            self.puppet_apt_pkg = 'puppet-agent'
            self.puppet_srvc = None
        else:
            raise PuppetException("puppet-srvc option value '{}' unkown. \
                Please change this option in the puppet-base layer options.")


    def install_puppet_apt_src(self):
        '''Fetch and install the puppet gpg key and puppet deb source
        '''
        hookenv.status_set('maintenance',
                           'Configuring Puppetlabs apt sources')
        # Add puppet gpg id and apt source
        charms.apt.add_source(self.puppet_apt_src, key=self.puppet_gpg_key)
        # Apt update to pick up the sources
        charms.apt.update()


    def install_puppet_apt_pkg(self):
        '''Install puppet pkg/enable srvc
        '''
        hookenv.status_set('maintenance',
                           'Installing %s' % self.puppet_apt_pkg)
        self.install_puppet_apt_src()
        # Queue the installation of appropriate puppet pkgs
        charms.apt.queue_install(self.puppet_apt_pkg)
        charms.apt.install_queued()


    def install_puppet_deps(self):
        '''Install the dependencies stored in `files/puppet/modules`
        '''
        if os.path.isfile('files/puppet/modules.tgz'):
            hookenv.status_set('maintenance',
                               'Installing puppet dependencies')
            with tarfile.open('files/puppet/modules.tgz', "r:gz") as tar:
                tar.extractall(path='files/puppet')
            try:
                os.makedirs(self.modules_dir)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise
            copy_tree('files/puppet/modules', self.modules_dir)


    def enable_service(self):
        '''Enable service of the package installed. Will not do anything if
        standalone mode.
        '''
        if self.puppet_srvc:
            check_call([self.puppet_exe, 'recource',
                        'service', self.puppet_srvc, 'ensure=running'])


    def apply(self, path):
        '''Run `puppet apply` on given path.
        '''
        check_call([self.puppet_exe, 'apply', path])


    def facter(self, argument=None):
        ''' return output of `facter` as a dict
        '''
        output = check_output([self.facter_exe, '-j', argument], universal_newlines=True)
        return json.loads(output)
