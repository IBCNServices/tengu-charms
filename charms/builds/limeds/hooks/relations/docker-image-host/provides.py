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

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes

from charmhelpers.core import hookenv


class DockerImageHostProvides(RelationBase):
    scope = scopes.UNIT

    @hook('{provides:docker-image-host}-relation-changed')
    def changed(self):
        self.set_state('{relation_name}.available')

    @hook('{provides:docker-image-host}-relation-{departed,broken}')
    def broken(self):
        hookenv.log(self.conversation().get_remote('image'))
        self.remove_state('{relation_name}.available')

    @property
    def images(self):
        images = []
        for conv in self.conversations():
            image = conv.get_remote('image')
            if image:
                images.append({
                    'daemon': conv.get_remote('daemon', True),
                    'interactive': conv.get_remote('interactive', True),
                    'ports': json.loads(conv.get_remote('ports', '[]')),
                    'name': conv.get_remote('name', False),
                    'image': image,
                    'username': conv.get_remote('username', ''),
                    'secret': conv.get_remote('secret', ''),
                })
        return images

    def send_published_ports(self, ports):
        conv = self.conversation()
        conv.set_remote('published_ports', json.dumps(ports))
