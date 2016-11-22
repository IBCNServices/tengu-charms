#python3 pylint:disable=c0111
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

from charmhelpers.core import unitdata

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class Neo4JRequires(RelationBase):
    
    scope = scopes.GLOBAL

    # These remote data fields will be automatically mapped to accessors
    # with a basic documentation string provided.
    auto_accessors = ['hostname', 'port']

    @hook('{requires:mongodb}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.connected')

    @hook('{requires:mongodb}-relation-changed')
    def changed(self):
        if self.connection_string():
            self.set_state('{relation_name}.database.available')
        else:
            self.set_state('{relation_name}.removed')

    @hook('{requires:mongodb}-relation-{broken,departed}')
    def broken_departed(self):
        self.remove_state('{relation_name}.connected')

    @hook('{requires:mongodb}-relation-broken')
    def broken(self):
        self.set_state('{relation_name}.removed')

    def connection_string(self):
        """
        Get the connection string, if available, or None.
        """
        data = {
            'hostname': self.hostname(),
            'port': self.port(),
        }
        if all(data.values()):
            return str.format('{hostname}:{port}', **data)
return None
