#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
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

from uuid import uuid4

from charmhelpers.core import hookenv, unitdata
from charmhelpers.core.hookenv import status_set, log

from charms.reactive import when, when_not
from charms.reactive.helpers import data_changed


@when_not('dockerhost.available')
def no_host_connected():
    # Reset so that `data_changed` will return "yes" at next relation joined.
    data_changed('image', None)
    status_set(
        'blocked',
        'Please connect the LimeDS charm to a docker host.')


@when('dockerhost.available')
def host_connected(dh_relation):
    conf = hookenv.config()
    if not data_changed('image', conf.get('image')):
        print("same, skipping")
        return
    print("Different")
    log('config.changed.image, generating new UUID')
    uuid = str(uuid4())
    container_request = {
        'image': conf.get('image'),
    }
    unitdata.kv().set('image', container_request)
    dh_relation.send_container_requests({uuid: container_request})
    status_set('waiting', 'Waiting for image to come online.')


@when('dockerhost.available')
def image_running(dh_relation):
    conf = hookenv.config()
    containers = dh_relation.get_running_containers()
    if containers:
        status_set('active', 'Ready ({})'.format(conf.get('image')))


@when('endpoint.available', 'dockerhost.available')
def configure_endpoint(endpoint_relation, dh_relation):
    containers = dh_relation.get_running_containers()
    # WARNING! This will only send the info of the last container!
    for container in containers:
        endpoint_relation.configure(
            hostname=container['host'],
            private_address=container['host'],
            port=container['ports']['8080'])


@when('limeds-server.available', 'dockerhost.available')
def configure_server(limeds_server_relation, dh_relation):
    containers = dh_relation.get_running_containers()
    # WARNING! This will only send the info of the last container!
    for container in containers:
        limeds_server_relation.configure(
            'http://{}:{}'.format(
                container['host'],
                container['ports']['8080'], )
        )
