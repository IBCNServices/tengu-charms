# python3 pylint:disable=c0111
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
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class OozieRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:oozie}-relation-{joined,changed}')
    def changed(self):
        if self.get_remote('private-address'):
            conv = self.conversation()
            # TODO: Implement new relationship protocol that indicates when oozie is ready
            conv.set_state('{relation_name}.joined')
            conv.set_state('{relation_name}.ready')
            print('wololo')


    @hook('{requires:oozie}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.ready')
        conv.remove_state('{relation_name}.joined')


    @property
    def port(self):
        """ Return Oozie port"""
        # TODO: implement new relationship protocol that sends port number
        conv = self.conversation()
        print('port')
        return conv.get_remote('port', str(11000))


    @property
    def private_address(self):
        """ return Oozie private address """
        print('pa')
        conv = self.conversation()
        return conv.get_remote('private-address')
