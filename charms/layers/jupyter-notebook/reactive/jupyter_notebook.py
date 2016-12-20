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
from charmhelpers.core import templating, hookenv, host, unitdata
from charmhelpers.contrib.python.packages import pip_install
from charmhelpers.core.hookenv import open_port, status_set
from charms.reactive import hook, when, when_not, set_state
from charms.reactive.helpers import data_changed


@hook('upgrade-charm')
def upgrade_charm():
    hookenv.log("Upgrading Notebook Charm")
    pip_install('jupyter', upgrade=True)


@when('apt.installed.python3-pip')
@when_not('jupyter-notebook.installed')
def install_jupyter_notebook():
    hookenv.log("Install Jupyter-notebook")
    pip_install('pip', upgrade=True)
    pip_install('jupyter')
    set_state('jupyter-notebook.installed')


@when('jupyter-notebook.installed')
@when('config.changed')
def configure_jupyter_notebook():
    conf = hookenv.config()
    jupyter_dir = '/opt/jupyter'
    port = conf['open-port']
    # Get or create and get password
    kv_store = unitdata.kv()
    password = kv_store.get('password')
    if not password:
        password = generate_password()
        kv_store.set('password', password)
    password_hash = generate_hash(password)
    context = {
        'port': port,
        'password_hash': password_hash,
    }
    if data_changed('jupyter-conf', context):
        # Create config directory and render config file
        host.mkdir(jupyter_dir)
        templating.render(
            source='jupyter_notebook_config.py.jinja2',
            target=jupyter_dir + '/jupyter_notebook_config.py',
            context=context
        )
        # Generate upstart template / service file
        render_api_upstart_template()
        restart_notebook()


def restart_notebook():
    # Start notebook and ensure it is running. Note that if the actual config
    # file is broken, the notebook will be running but won't be accessible from
    # anywhere else then localhost.
    host.service_restart('jupyter')
    if host.service_running('jupyter'):
        status_set('active',
                   'Ready (Pass: "{}")'.format(unitdata.kv().get('password')))
        open_port(hookenv.config()['open-port'])
        set_state('jupyter-notebook.configured')
    else:
        status_set('blocked',
                   'Could not restart service due to wrong configuration!')


def render_api_upstart_template():
    templating.render(
        source='upstart.conf',
        target='/etc/init/jupyter.conf',
        context={}
        )

#
# Helper functions
#

def generate_hash(password):
    from notebook.auth import passwd
    return passwd(password)


def generate_password():
    from xkcdpass import xkcd_password as xp
    mywords = xp.generate_wordlist()
    return xp.generate_xkcdpassword(mywords, numwords=4)
