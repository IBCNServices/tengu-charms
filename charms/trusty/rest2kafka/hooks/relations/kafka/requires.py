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


class KafkaRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:kafka}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{requires:kafka}-relation-changed')
    def changed(self):
        conv = self.conversation()
        if self.kafkas() and self.zookeepers():
            conv.set_state('{relation_name}.ready')
        else:
            conv.remove_state('{relation_name}.ready')

    @hook('{requires:kafka}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.ready')
        conv.remove_state('{relation_name}.joined')

    def kafkas(self):
        kafkas = []
        for conv in self.conversations():
            port = conv.get_remote('port')
            if port:
                kafkas.append({
                    'host': conv.get_remote('private-address'),
                    'port': port
                })
        return kafkas

    def zookeepers(self):
        """
        Returns Zookeeper connection info

        :returns: List of ZK entry dicts.  Each dict will
            contain a ``host``, ``port``, and ``rest_port`` key.
        """
        zookeepers = []
        for conv in self.conversations():
            zks = json.loads(conv.get_remote('zookeepers', '[]'))
            for zk in zks:
                zookeepers.append({
                    'host': zk['host'],
                    'port': zk['port'],
                    'rest_port': zk['rest_port'],
                })
        return zookeepers
