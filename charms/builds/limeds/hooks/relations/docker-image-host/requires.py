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
        host = conv.get_remote('private-address')
        host_ports = conv.get_remote('published_ports')
        if host and host_ports:
            conv.set_state('{relation_name}.ready')


    @hook('{requires:docker-image-host}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')

    def send_configuration(self, name, image, ports=None, username=None,
                           secret=None, daemon=True, interactive=True):#pylint:disable=R0913
        if not ports:
            ports = []
        conv = self.conversation()
        conv.set_remote('image', image)
        conv.set_remote('username', username)
        conv.set_remote('secret', secret)
        conv.set_remote('name', name)
        conv.set_remote('daemon', daemon)
        conv.set_remote('interactive', interactive)
        conv.set_remote('ports', json.dumps(ports))


    def get_running_image(self):
        conv = self.conversation()
        host = conv.get_remote('private-address')
        host_ports = conv.get_remote('published_ports')
        if host and host_ports:
            print("host_ports string: {}".format(host_ports))
            return (host, yaml.load(host_ports))
        return None
