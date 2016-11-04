#!/usr/bin/env python3
# Copyright (C) 2016  Ghent University
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
# pylint: disable=C0111,C0103,c0325
import os
import pwd
import grp

from charms import reactive, apt #pylint:disable=e0611
from charms.reactive import hook
from charmhelpers.core import hookenv

USER = hookenv.config()['user']
HOME = os.path.expanduser('~{}'.format(USER))


@hook('install')
def install():
    hookenv.status_set('maintenance', 'Installing Juju client')
    install_packages()
    reactive.set_state('juju.installed')
    hookenv.status_set('maintenance', 'Juju client installed')


@hook('upgrade-charm')
def upgrade():
    install()
    reactive.set_state('juju.upgraded')


def install_packages():
    apt.add_source('ppa:juju/stable')
    apt.update()
    packages = ['juju', 'juju-core', 'juju-deployer',
                'git', 'python-yaml', 'python-jujuclient', 'charm-tools']
    apt.queue_install(packages)
    apt.install_queued()

#
#
## HELPERS
#
#

def chownr(path, owner, group, follow_links=True):
    uid = pwd.getpwnam(owner).pw_uid
    gid = grp.getgrnam(group).gr_gid
    if follow_links:
        chown = os.chown
    else:
        chown = os.lchown
    chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            full = os.path.join(root, name)
            broken_symlink = os.path.lexists(full) and not os.path.exists(full)
            if not broken_symlink:
                chown(full, uid, gid)
