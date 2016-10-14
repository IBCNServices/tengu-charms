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
# pylint: disable=c0111,c0103,c0301
import subprocess
import os
import json
import shutil

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port, status_set
from charms.reactive import hook, when, when_not, set_state

import charms.apt #pylint: disable=e0611,e0401

@hook('upgrade-charm')
def upgrade_charm():
    """Upgrade Charm"""
    hookenv.log("Upgrading rest2maas Charm")
    try:
        subprocess.check_output(['service', 'rest2maas', 'stop'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        # we do not need to exit here
    install()

@when_not('apt.installed.python-pip')
def pre_install():
    hookenv.log("Pre-install")
    charms.apt.queue_install(['python-pip', 'maas-cli'])#pylint: disable=e1101

@when('apt.installed.python-pip')
@when_not('rest2maas.installed')
def install():
    """Install rest2maas"""
    subprocess.check_call(['hostnamectl', 'set-hostname', 'rest2maas'])
    try:
        # update needed because of weird error
        hookenv.log("Installing dependencies")
        subprocess.check_output(['apt-get', 'update'])
        subprocess.check_output(['pip3', 'install', 'Jinja2', 'Flask', 'pyyaml', 'click', 'python-dateutil'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        exit(1)
    mergecopytree(charm_dir() + '/files/rest2maas', "/opt/rest2maas")
    hookenv.log("Extracting and moving required files and folders")
    hookenv.log("Generating upstart file")
    with open(charm_dir()+'/templates/upstart.conf', 'r') as upstart_t_file:
        upstart_template = upstart_t_file.read()
    with open('/etc/init/rest2maas.conf', 'w') as upstart_file:
        upstart_file = upstart_file.write(upstart_template)
    hookenv.log("Starting rest2maas service")
    try:
        subprocess.check_output(['service', 'rest2maas', 'start'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        exit(1)
    open_port(5000)
    status_set('active', 'Ready')
    set_state('rest2maas.installed')

@hook('config-changed')
def config_changed():
    """Config changed"""
    hookenv.log('Reconfiguring rest2maas')
    conf = hookenv.config()
    maas_config = {
        'username': conf['maas-username'],
        'password': conf['maas-password'],
        'url': conf['maas-url'],
    }
    with open('/opt/rest2maas/config.json', 'w+') as config_file:
        config_file.write(json.dumps(maas_config))
        config_file.truncate()

@when('rest2maas.available')
def configure_rest2maas_relation(relation):
    relation.configure(port='5000')

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
