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

import json

from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes

from jujubigdata import utils


class DataNodeRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:dfs-slave}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')
        conv.remove_state('{relation_name}.departing')

    @hook('{requires:dfs-slave}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.joined')
        conv.set_state('{relation_name}.departing')

    def dismiss(self):
        for conv in self.conversations():
            conv.remove_state('{relation_name}.departing')

    def nodes(self):
        return [
            {
                'host': conv.scope.replace('/', '-'),
                'ip': utils.resolve_private_address(
                    conv.get_remote('private-address', '')),
            }
            for conv in self.conversations()
        ]

    def send_spec(self, spec):
        for conv in self.conversations():
            conv.set_remote('spec', json.dumps(spec))

    def send_namenodes(self, namenodes):
        for conv in self.conversations():
            conv.set_remote('namenodes', json.dumps(namenodes))

    def send_ports(self, port, webhdfs_port):
        for conv in self.conversations():
            conv.set_remote(data={
                'port': port,
                'webhdfs-port': webhdfs_port,
            })

    def send_ssh_key(self, ssh_key):
        for conv in self.conversations():
            conv.set_remote('ssh-key', ssh_key)

    def send_hosts_map(self, hosts_map):
        for conv in self.conversations():
            conv.set_remote('etc_hosts', json.dumps(hosts_map))
