#!/usr/bin/env python3
import subprocess
import os

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port, status_set
from charms.reactive import when, when_not, set_state

import charms.apt

@when('java.installed')
@when_not('testneo4j.installed')
def install_testneo4j():
    hookenv.log("Installing Neo4J")
    subprocess.check_call('wget -O - https://debian.neo4j.org/neotechnology.gpg.key | sudo apt-key add -', shell=True)
    subprocess.check_call("echo 'deb http://debian.neo4j.org/repo stable/' | sudo tee -a /etc/apt/sources.list.d/neo4j.list > /dev/null", shell=True)
    subprocess.check_call(['apt-get','update']) 
    charms.apt.queue_install(['neo4j'])
    
    status_set('active', 'Ready')
    set_state('testneo4j.installed')

