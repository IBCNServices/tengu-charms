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

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port, status_set
from charms.reactive import hook, when, when_not, set_state

import charms.apt #pylint: disable=e0611,e0401


@when_not('apt.installed.python-pip', 'jupyter-notebook.installed')
def pre_install():
    hookenv.log("Pre-install")
    charms.apt.queue_install(['python-pip','python3-pip'])#pylint: disable=e1101

@when('apt.installed.python-pip')
@when_not('jupyter-notebook.installed')
def install_jupyter_notebook():
    hookenv.log("Install Jupyter-notebook")
    subprocess.check_call(['pip3','install','--upgrade','pip'])
    subprocess.check_call(['pip3','install','jupyter'])
    hookenv.status_set('active','Ready')
    set_state('jupyter-notebook.installed')
