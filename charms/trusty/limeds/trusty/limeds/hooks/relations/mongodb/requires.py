#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes


class MongoDBClient(RelationBase):
    # We only expect a single mongodb server to be related.  Additionally, if
    # there are multiple units, it would be for replication purposes only,
    # so we would expect a leader to provide our connection info, or at least
    # for all mongodb units to agree on the connection info.  Thus, we use a
    # global conversation scope in which all services and units share the
    # same conversation.
    # TODO (mattyw, cmars) Talk to cory about this.
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
