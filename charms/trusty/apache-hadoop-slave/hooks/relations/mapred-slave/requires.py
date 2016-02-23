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


class NodeManagerRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:mapred-slave}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.related')
        conv.remove_state('{relation_name}.departing')

    @hook('{requires:mapred-slave}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.related')
        conv.set_state('{relation_name}.departing')

    def dismiss(self):
        for conv in self.conversations():
            conv.remove_state('{relation_name}.departing')

    def nodes(self):
        return [
            {
                'host': conv.scope.replace('/', '-'),
                'ip': utils.resolve_private_address(conv.get_remote('private-address', '')),
            }
            for conv in self.conversations()
        ]

    def send_spec(self, spec):
        for conv in self.conversations():
            conv.set_remote('spec', json.dumps(spec))

    def send_resourcemanagers(self, resourcemanagers):
        for conv in self.conversations():
            conv.set_remote('resourcemanagers', json.dumps(resourcemanagers))

    def send_ports(self, port, hs_http, hs_ipc):
        for conv in self.conversations():
            conv.set_remote(data={
                'port': port,
                'historyserver_http': hs_http,
                'historyserver_ipc': hs_ipc,
            })

    def send_ssh_key(self, ssh_key):
        for conv in self.conversations():
            conv.set_remote('ssh-key', ssh_key)

    def send_hosts_map(self, hosts_map):
        for conv in self.conversations():
            conv.set_remote('etc_hosts', json.dumps(hosts_map))
