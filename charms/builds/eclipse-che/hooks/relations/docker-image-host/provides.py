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


class DockerImageHostProvides(RelationBase):
    scope = scopes.UNIT

    @hook('{provides:docker-image-host}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.available')

    @hook('{provides:docker-image-host}-relation-{departed,broken}')
    def broken(self):
        self.remove_state('{relation_name}.available')

    @property
    def container_requests(self):
        container_requests = {}
        for conv in self.conversations():
            conv_con_reqs = yaml.safe_load(
                conv.get_remote('container-requests', "{}"))
            conv.set_local(
                'uuids',
                list(conv_con_reqs.keys()))
            container_requests.update(conv_con_reqs)
        return container_requests

    def send_running_containers(self, containers):
        for conv in self.conversations():
            conts_to_send = {}
            uuids = conv.get_local('uuids', [])
            for uuid in uuids:
                conts_to_send[uuid] = containers[uuid]
            conv.set_remote('running-containers', json.dumps(conts_to_send))
