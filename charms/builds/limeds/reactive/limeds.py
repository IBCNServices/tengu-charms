#!/usr/bin/env python3 pylint:disable=c0111
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

# pylint:disable=c0301,c0103

from charmhelpers.core import hookenv

from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state, is_state


@when('config.changed')
def reconfigure_docker_host():
    hookenv.log(hookenv.relation_get('dockerhost'))
    if is_state('dockerhost.available') and is_state('limeds.ready'):
        conf = hookenv.config()
        hookenv.status_set(
            'maintenance',
            'Reconfiguring LimeDS [{}].'.format(conf.get('image')))
        remove_state('limeds.ready')


@when_not('dockerhost.available')
def no_host_connected():
    hookenv.status_set(
        'blocked',
        'Please connect the LimeDS charm to a docker host.')
    if is_state('limeds.ready'):
        remove_state('limeds.ready')


@when('dockerhost.available')
@when_not('limeds.ready')
def host_connected(dh):
    conf = hookenv.config()
    hookenv.log(
        'configure_docker_host invoked \
        for unit {}!!'.format(hookenv.local_unit()))
    hookenv.status_set('maintenance', 'Sending configuration to host.')
    name = hookenv.local_unit().replace("/", "-")
    ports = ['8080', '8443']
    dh.send_configuration(
        name,
        conf.get('image'),
        ports,
        conf.get('username'),
        conf.get('secret'),
        True,
        True)
    hookenv.status_set('waiting', 'Waiting for image to come online.')


@when('dockerhost.ready')
def image_running(dh):  # pylint:disable=W0611,W0613
    conf = hookenv.config()
    hookenv.status_set('active', 'Ready ({})'.format(conf.get('image')))
    set_state('limeds.ready')


@when('endpoint.available', 'dockerhost.ready', 'limeds.ready')
def configure_endpoint(endpoint, dh):
    (docker_host, docker_host_ports) = dh.get_running_image()
    hookenv.log('The IP of the docker host is {}.'.format(docker_host))
    endpoint.configure(
        hostname=docker_host,
        private_address=docker_host,
        port=docker_host_ports['8080'])
