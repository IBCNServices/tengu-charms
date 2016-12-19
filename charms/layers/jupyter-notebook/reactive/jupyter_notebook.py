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
from charmhelpers.core import templating, hookenv, host
from charmhelpers.contrib.python.packages import pip_install
from charmhelpers.core.hookenv import open_port, status_set
from charms.reactive import hook, when, when_not, set_state


@hook('upgrade-charm')
def upgrade_charm():
    hookenv.log("Upgrading Notebook Charm")
    pip_install('jupyter', upgrade=True)
#
@when('spark.ready')
@when_not('jupyter-notebook.installed')
def install_jupyter_notebook():
    hookenv.log("Install Jupyter-notebook")
    pip_install('pip', upgrade=True)
    pip_install('jupyter')
    set_state('jupyter-notebook.installed')


@when('jupyter-notebook.installed')
def configure_jupyter_notebook():
    conf = hookenv.config()
    jupyter_dir = '/opt/jupyter'
    host.mkdir(jupyter_dir)
    hookenv.log('Configuring jupyter-notebook upstart')
    render_api_upstart_template()
    hookenv.log('Generating jupyter notebook config')
    render_default_config_template(jupyter_dir)
    host.service_restart('jupyter')
    if host.service_running('jupyter'):
        status_set('active', 'Ready')
        open_port(conf['open-port'])
        set_state('jupyter-notebook.configured')
    else:
        status_set('blocked', 'Could not restart service due to wrong configuration!')
#
#@when('jupyter-notebook.started')
#@when_not('spark.ready')
#def stop_jupyter():
#    subprocess.check_call(['service','jupyter','stop'])
#    remove_state('zeppelin.started')


# template functions

def render_api_upstart_template():
    templating.render(
        source='upstart.conf',
        target='/etc/init/jupyter.conf',
        context={}
        )

def render_default_config_template(jupyter_dir):
    conf = hookenv.config()
    port = conf['open-port']
    templating.render(
        source='config_template.py',
        target=jupyter_dir + '/jupyter_notebook_config.py',
        context={
            'port': port
        }
    )
