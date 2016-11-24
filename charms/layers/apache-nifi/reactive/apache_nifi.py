# pylint: disable=C0111, C0301

import subprocess
import tarfile

from charms.reactive import when, when_not, set_state, remove_state
from charmhelpers.core import hookenv
from charmhelpers.core.host import service_restart, service_stop
from charmhelpers.core.templating import render


@when_not('apache-nifi.installed')
@when('java.installed')
def install_apache_nifi():
    conf = hookenv.config()
    hookenv.log('Installing Apache NiFi')
    hookenv.status_set('maintenance', 'Installing Apache NiFi')
    tfile = tarfile.open(hookenv.resource_get('apache-nifi'), 'r')
    filesdir = '%s/files' % hookenv.charm_dir()
    tfile.extractall(filesdir)
    render(source='nifi.properties', target='%s/nifi-1.0.0/conf/nifi.properties' % filesdir,
           context={'nifi_port': conf['nifi-port']}
          )
    subprocess.check_call(['bash', '%s/nifi-1.0.0/bin/nifi.sh' % filesdir, 'install'])
    service_restart('nifi')
    hookenv.open_port(conf['nifi-port'])
    hookenv.status_set('active', 'Apache NiFi has been installed and is running in standalone mode')
    set_state('apache-nifi.installed')


@when('apache-nifi.installed')
@when('zookeeper.joined')
@when_not('zookeeper.ready')
def zookeeper_wait(zookeeper):
    hookenv.status_set('waiting', 'Waiting for Zookeeper to become available')


@when('zookeeper.ready')
@when('apache-nifi.installed')
@when_not('apache-nifi.cluster')
def zookeeper_config(zookeeper):
    hookenv.status_set('maintenance', 'Changing Apache NiFi to run as a cluster')
    hookenv.log('Adding Apache Zookeeper -- Changing Apache NiFi to run as a cluster')
    conf = hookenv.config()
    zookeeper_servers = []
    zookeeper_servers_string = ''
    for zk_unit in zookeeper.zookeepers():
        zookeeper_servers.append((zk_unit['host'], zk_unit['port']))
        zookeeper_servers_string += '%s:%s,' % (zk_unit['host'], zk_unit['port'])
    render(source='nifi.properties',
           target='%s/files/nifi-1.0.0/conf/nifi.properties' % hookenv.charm_dir(),
           context={'nifi_cluster': 'true',
                    'node_address': hookenv.unit_public_ip(),
                    'nifi_port': conf['nifi-port'],
                    'zookeeper_port': conf['cluster-port'],
                    'zookeeper_servers': zookeeper_servers_string[:-1]})
    service_restart('nifi')
    set_state('apache-nifi.cluster')
    hookenv.status_set('active', 'Apache NiFi is running in a cluster with Apache Zookeeper')


@when('apache-nifi.cluster')
@when_not('zookeeper.joined', 'zookeeper.ready')
def zookeeper_removed(zookeeper):
    hookenv.status_set('maintenance', 'Removing Apache NiFi from cluster')
    render(source='nifi.properties',
           target='%s/files/nifi-1.0.0/conf/nifi.properties' % hookenv.charm_dir(),
           context={'nifi-cluster': 'false'})
    service_stop('nifi')
    remove_state('apache-nifi.cluster')
    hookenv.status_set('waiting', 'Apache NiFi is configured for standalone mode, but not running')
