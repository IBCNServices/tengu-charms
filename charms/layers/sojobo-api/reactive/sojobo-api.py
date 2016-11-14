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
import os
from os.path import expanduser
import shutil
import tempfile
import subprocess

# Charm pip dependencies
from charmhelpers.core import templating
from charmhelpers.core.hookenv import (
    status_set,
    log,
    config,
    open_port
)
from charmhelpers.core.host import service_restart, chownr
from charmhelpers.contrib.python.packages import pip_install

from charms.reactive import hook, when, when_not, set_state


API_DIR = '/opt/sojobo-api'
USER = config()['user']
HOME = expanduser('~{}'.format(USER))
SSH_DIR = HOME + '/.ssh'


###############################################################################
#
# INSTALLATION AND UPGRADES
#
###############################################################################

@when('juju.installed')
@when_not('api.installed')
def install():
    log('Installing Sojobo API')
    install_api()
    set_state('api.installed')


@hook('upgrade-charm')
def upgrade_charm():
    log('Updating Sojobo API')
    install_api()
    set_state('api.installed')


def install_api():
    """Installs api management pkgs
    """

    # Install pip pkgs
    for pkg in ['Jinja2', 'Flask', 'pyyaml', 'click', 'pygments', 'lxml',
                'apscheduler']:
        pip_install(pkg)

    # Install The Sojobo API. Existing /etc files don't get overwritten.
    if os.path.isdir(API_DIR + '/etc'):
        t_etc_dir = tempfile.mkdtemp()
        mergecopytree(API_DIR + '/etc', t_etc_dir)
        mergecopytree('files/sojobo-api', API_DIR)
        mergecopytree(t_etc_dir, API_DIR + '/etc')
    else:
        mergecopytree('files/sojobo-api', API_DIR)

    # setup api
    render_api_systemd_template()
    # USER should get all access rights.
    chownr(API_DIR, USER, USER, chowntopdir=True)
    subprocess.check_call(['systemctl', 'enable', 'sojobo-api'])
    success = service_restart('sojobo-api')
    if not success:
        print("Error: starting service failed!")
        exit(1)
    open_port('5000')
    open_port('22')
    status_set('active', 'Ready')


def render_api_systemd_template():
    appconf = config()
    env_vars = [
        "MAAS_USER={}".format(appconf['maas-user']),
        "MAAS_API_KEY={}".format(appconf['maas-api-key']),
        "MAAS_URL={}".format(appconf['maas-url']),
        "JUJU_USER={}".format(appconf['juju-username']),
        "JUJU_PASSWORD={}".format(appconf['juju-password']),
        "CONTROLLER_NAME={}".format(appconf['juju-controller']),
    ]

    flags = appconf['feature-flags'].replace(' ', '')
    flags = [x for x in flags.split(',') if x != '']
    templating.render(
        source='flask-app.service',
        target='/etc/systemd/system/sojobo-api.service',
        context={
            'description': "The Sojobo API",
            'application_dir': API_DIR,
            'application_path': "{}/sbin/sojobo_api.py".format(API_DIR),
            'user': USER,
            'flags': flags,
            'env_vars': env_vars,
        }
    )
    subprocess.check_call(['systemctl', 'daemon-reload'])


###############################################################################
#
# Handeling changed configs
#
###############################################################################


@when('api.installed')
@when('config.changed.feature-flags')
def feature_flags_changed():
    render_api_systemd_template()
    service_restart('sojobo-api')


###############################################################################
#
# UTILS
#
###############################################################################

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
