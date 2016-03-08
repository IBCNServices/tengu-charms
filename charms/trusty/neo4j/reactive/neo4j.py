#!/usr/bin/python3 pylint:disable=c0111

from jujubigdata import utils

from charmhelpers import fetch
from charmhelpers.core.host import service_restart
from charmhelpers.core import hookenv
from charms.reactive import when_not, set_state


@when_not('neo4j.installed')
def install():
    hookenv.log('Installing neo4j')
    config = hookenv.config()
    hookenv.open_port(config['port'])
    fetch.configure_sources(True)
    fetch.apt_install(fetch.filter_installed_packages(['neo4j']))
    utils.re_edit_in_place('/etc/neo4j/neo4j-server.properties', {
        r'#org.neo4j.server.webserver.address=0.0.0.0': 'org.neo4j.server.webserver.address=0.0.0.0',
    })
#    utils.re_edit_in_place('/etc/security/limits.conf', {
#        r'#org.neo4j.server.webserver.address=127.0.0.1': 'org.neo4j.server.webserver.address=0.0.0.0',
#    })
    service_restart('neo4j-service')
    set_state('neo4j.installed')
