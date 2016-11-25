# Copyright (C) 2016  Qrama
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
# pylint: disable=C0111, C0301

import subprocess
import tarfile

from charms.reactive import when, when_not, set_state, remove_state
from charmhelpers.core import hookenv
from charmhelpers.core.host import service_restart, service_stop

from jujubigdata.utils import re_edit_in_place


@when_not('apache-nifi.installed')
@when('java.installed')
def install_apache_nifi():
    conf = hookenv.config()
    hookenv.log('Installing Apache NiFi')
    hookenv.status_set('maintenance', 'Installing Apache NiFi')
    tfile = tarfile.open(hookenv.resource_get('apache-nifi'), 'r')
    filesdir = '%s/files' % hookenv.charm_dir()
    tfile.extractall(filesdir)
    re_edit_in_place('%s/nifi-1.0.0/conf/nifi.properties' % filesdir, {
        r'.*nifi.web.http.port.*': 'nifi.web.http.port=%s' % conf['nifi-port'],
    })
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


@when('zookeeper.ready', 'apache-nifi.installed')
@when_not('apache-nifi.cluster')
def zookeeper_config(zookeeper):
    hookenv.status_set('maintenance', 'Changing Apache NiFi to run as a cluster')
    hookenv.log('Adding Apache Zookeeper -- Changing Apache NiFi to run as a cluster')
    conf = hookenv.config()
    zookeeper_servers_string = ''
    for zk_unit in zookeeper.zookeepers():
        zookeeper_servers_string += '%s:%s,' % (zk_unit['host'], zk_unit['port'])
    re_edit_in_place('%s/files/nifi-1.0.0/conf/nifi.properties' % hookenv.charm_dir(), {
        r'.*nifi.cluster.is.node.*': 'nifi.cluster.is.node=true',
        r'.*nifi.cluster.node.address.*': 'nifi.cluster.node.address=%s' % hookenv.unit_public_ip(),
        r'.*nifi.web.http.port.*': 'nifi.web.http.port=%s' % conf['nifi-port'],
        r'.*nifi.cluster.node.protocol.port.*': 'nifi.cluster.node.protocol.port=%s' % conf['cluster-port'],
        r'.*nifi.zookeeper.connect.string.*': 'nifi.zookeeper.connect.string=%s' % zookeeper_servers_string
    })
    service_restart('nifi')
    set_state('apache-nifi.cluster')
    hookenv.status_set('active', 'Apache NiFi is running in a cluster with Apache Zookeeper')


@when('zookeeper.ready', 'apache-nifi.installed', 'apache-nifi.cluster')
def zookeeper_changed(zookeeper):
    hookenv.log('Checking if Zookeeper has changed')
    zookeeper_servers_string = ''
    filesdir = '%s/files' % hookenv.charm_dir()
    for zk_unit in zookeeper.zookeepers():
        zookeeper_servers_string += '%s:%s,' % (zk_unit['host'], zk_unit['port'])
    if zookeeper_servers_string[:-1] not in open('%s/nifi-1.0.0/conf/nifi.properties' % filesdir).read():
        hookenv.status_set('maintenance', 'Zookeeper has changed. Updating Apache NiFi settings and restarting')
        re_edit_in_place('%s/nifi-1.0.0/conf/nifi.properties' % filesdir, {
            r'.*nifi.zookeeper.connect.string.*': 'nifi.zookeeper.connect.string=%s' % zookeeper_servers_string[:-1]
        })
        service_restart('nifi')
        hookenv.status_set('active', 'Apache NiFi is running in a cluster with Apache Zookeeper')


@when('apache-nifi.cluster')
@when_not('zookeeper.joined', 'zookeeper.ready')
def zookeeper_removed():
    hookenv.status_set('maintenance', 'Removing Apache NiFi from cluster')
    re_edit_in_place('%s/files/nifi-1.0.0/conf/nifi.properties' % hookenv.charm_dir(), {
        r'.*nifi.cluster.is.node.*': 'nifi.cluster.is.node=false'
    })
    service_stop('nifi')
    remove_state('apache-nifi.cluster')
    hookenv.status_set('waiting', 'Apache NiFi is configured for standalone mode, but not running')
