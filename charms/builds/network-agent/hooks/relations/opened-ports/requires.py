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

from charmhelpers.core import unitdata

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes

RANGE = 29000

KV = unitdata.kv()


class OpenedPortsRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:opened-ports}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('opened-ports'):
            # this unit's conversation has a port, so
            # it is part of the set of available units
            opened_ports = json.loads(conv.get_remote('opened-ports'))
            port_forwards = conv.get_local('port-forwards', [])
            # Get public ip address
            public_address = KV.get('public-ip')
            for portproto in opened_ports:
                if not any(
                        (pf['private_port'] == portproto['port']) and
                        (pf['protocol'] == portproto['protocol'])
                        for pf in port_forwards):
                    free_port = KV.get('freeport', RANGE)
                    KV.set('freeport', free_port + 1)
                    port_forward = {
                        "public_port": free_port,
                        "private_port": portproto['port'],
                        "public_ip": public_address,
                        "private_ip": conv.get_remote('private-address'),
                        "protocol": portproto['protocol'],
                    }
                    port_forwards.append(port_forward)
                    conv.set_local('port-forwards', port_forwards)
            conv.set_state('{relation_name}.available')

    @hook('{requires:opened-ports}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')

    @property
    def opened_ports(self):
        """ Returns list of dicts:  {
            "public_port": "<public-port>",
            "private_port": "<private_port>",
            "private_ip": "<private_ip>",
            "protocol": "<tcp/udp>"
        } . """
        services = []
        for conv in self.conversations():
            port_forwards = conv.get_local('port-forwards', [])
            services.extend(port_forwards)
        return services

    def set_ready(self):
        """ send a notice to the related charms that
        the port forwarding has been applied
        """
        for conv in self.conversations():
            conv.set_remote('port-forwards',
                            json.dumps(conv.get_local('port-forwards', [])))
