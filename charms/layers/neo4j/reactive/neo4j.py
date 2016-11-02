#!/usr/bin/env python3
import subprocess
import os

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port, status_set
from charms.reactive import hook, when, when_not, set_state

import charms.apt

@hook('upgrade-charm')
def upgrade_charm():
    hookenv.log("Upgrading neo4j Charm")
    try:
        subprocess.check_call(['service','neo4j','stop'])
    except subprocess.CalledProcessError as exception:
        hooken.log(exception.output)
    install()

@when('java.installed')
@when_not('apt.installed.python-pip')
def pre_install():
    hookenv.log("Install Python-pip")
    charms.apt.queue_install(['python-pip'])#pylint: disable=e1101

@when('java.installed','apt.installed.python-pip')
@when_not('neo4j.installed')
def install():
    hookenv.log("Installing Neo4J")
    conf = hookenv.config()
    charms.apt.queue_install(['neo4j'])
    charms.apt.install_queued()
    #install python driver if required
    python_type = conf['python-type']
    if python_type != 'none':
        subprocess.check_call(['pip','install',python_type])
        
    hookenv.status_set('active','Ready')
    set_state('neo4j.installed')

