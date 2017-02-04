#!/usr/bin/python3
# Copyright (c) 2016, James Beedy <jamesbeedy@gmail.com>
# Copyright (c) 2017, Ghent University
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

from charmhelpers.core import hookenv

from charms.reactive import when_not
from charms.reactive import set_state

from charms import layer  # pylint:disable=E0611,E0401
from charms.layer.puppet_base import (  # pylint:disable=E0611,E0401
    Puppet,
    PuppetException
)

options = layer.options('puppet-base')
puppet_service = options.get('puppet-srvc')

PUPPET_SERVICE_INSTALLED = "puppet.%s.installed" % puppet_service


@when_not(PUPPET_SERVICE_INSTALLED)
def install_puppet_agent():

    '''Install puppet pkg
    '''
    hookenv.status_set('maintenance',
                       'Installing puppet %s' % puppet_service)
    try:
        p = Puppet()
    except PuppetException as ex:
        print(ex.message)
        exit(1)
    p.install_puppet_apt_pkg()
    p.install_puppet_deps()
    set_state(PUPPET_SERVICE_INSTALLED)
