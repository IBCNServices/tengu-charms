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
    install_neo4j()

@when('java.installed')
@when_not('neo4j.installed')
def install_neo4j():
    hookenv.log("Installing Neo4J")
    #subprocess.check_call('wget -O - https://debian.neo4j.org/neotechnology.gpg.key | sudo apt-key add -', shell=True)
    #subprocess.check_call("echo 'deb http://debian.neo4j.org/repo stable/' | sudo tee -a /etc/apt/sources.list.d/neo4j.list > /dev/null", shell=True)
    #subprocess.check_call(['apt-get','update']) 
    charms.apt.queue_install(['neo4j'])
    charms.apt.install_queued()
    
    hookenv.status_set('active','Ready')
    set_state('neo4j.installed')

