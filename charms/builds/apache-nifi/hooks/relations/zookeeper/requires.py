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


class ZookeeperRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:zookeeper}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{requires:zookeeper}-relation-changed')
    def changed(self):
        conv = self.conversation()
        if self.zookeepers():
            conv.set_state('{relation_name}.ready')
        else:
            conv.remove_state('{relation_name}.ready')

    @hook('{requires:zookeeper}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.ready')
        conv.remove_state('{relation_name}.joined')

    def zookeepers(self):
        zks = []
        for conv in self.conversations():
            port = conv.get_remote('port')
            rest_port = conv.get_remote('rest_port')
            host = conv.get_remote('host') or conv.get_remote(
                'private-address')
            if port:
                zks.append({
                    'host': host,
                    'port': port,
                    'rest_port': rest_port
                })
        return zks
