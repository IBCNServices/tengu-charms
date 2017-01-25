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

import json
import yaml

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class DockerImageHostRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:docker-image-host}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.available')

    @hook('{requires:docker-image-host}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')

    def send_container_requests(self, container_requests):
        """ container_requests: {
            uuid: {
                image: <image>,
                #...
            },
            #...
        }
        """
        conv = self.conversation()
        conv.set_local(
            'uuids',
            list(container_requests.keys()))
        conv.set_remote(
            'container-requests',
            json.dumps(container_requests))

    def get_running_containers(self):
        conv = self.conversation()
        requested_uuids = conv.get_local('uuids', [])
        remote_containers = yaml.safe_load(
            conv.get_remote('running-containers', "{}"))
        containers_to_return = []
        for uuid in requested_uuids:
            remote_container = remote_containers.get(uuid)
            if remote_container:
                containers_to_return.append(remote_container)
        return containers_to_return
