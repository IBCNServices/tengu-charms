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
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class HttpRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:limeds}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('url'):
            # this unit's conversation has a port, so
            # it is part of the set of available units
            conv.set_state('{relation_name}.available')

    @hook('{requires:limeds}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')

    def units(self):
        """
        Returns a list of available limeds services and their associated hosts
        and ports.

        The return value is a list of dicts of the following form::

            [
                {
                    'url': <base url of limeds instance>,
                },
                # ...
            ]
        """
        services = []
        for conv in self.conversations():
            services.append(
                {
                    "url": conv.get_remote('url'),
                })
        return services
