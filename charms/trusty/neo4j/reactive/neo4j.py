#!/usr/bin/env python3
import subprocess
import os

from jujubigdata import utils
from charmhelpers.core import hookenv
from charmhelpers.core.host import service_start
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
    hookenv.open_port(conf['port'])
    charms.apt.queue_install(['neo4j'])
    #install python driver if required
    python_type = conf['python-type']
    if python_type != 'none':
        subprocess.check_call(['pip','install',python_type])

@when('apt.installed.neo4j')
def config_bindings():
    try:
        subprocess.check_call(['service','neo4j','stop'])
    except subprocess.CalledProcessError as exception:
        hooken.log(exception.output)
    utils.re_edit_in_place('/etc/neo4j/neo4j.conf', {
        r'#dbms.connector.http.address=0.0.0.0:7474': 'dbms.connector.http.address=0.0.0.0:7474',
    })
    service_start('neo4j')
    hookenv.status_set('active','Ready')
    set_state('neo4j.installed')

@when('config.changed.python-type')
def install_python_driver():
    conf = hookenv.config()
    python_type = conf['python-type']
    if python_type != 'none':
        subprocess.check_call(['pip','install',python_type])
