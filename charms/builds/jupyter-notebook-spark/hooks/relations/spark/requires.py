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


class SparkRequires(RelationBase):
    scope = scopes.GLOBAL

    def is_spark_started(self):
        return self.get_remote('spark_started', 'false').lower() == 'true'

    @hook('{requires:spark}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{requires:spark}-relation-changed')
    def changed(self):
        conv = self.conversation()
        conv.toggle_state('{relation_name}.ready',
                          active=self.is_spark_started())
        conv.toggle_state('{relation_name}.master',
                          active=all([
                              self.get_master_url(),
                              self.get_master_ip(),
                          ]))

    @hook('{requires:spark}-relation-departed')
    def departed(self):
        conv = self.conversation()
        if len(conv.units) <= 1:
            conv.remove_state('{relation_name}.joined')
            conv.remove_state('{relation_name}.ready')

    def get_private_ip(self):
        conv = self.conversation()
        return conv.get_remote('private-address')

    def get_rest_port(self):
        conv = self.conversation()
        return conv.get_remote('rest_port')

    def get_master_info(self):
        conv = self.conversation()
        data = {
            'connection_string': conv.get_remote('connection_string'),
            'master': conv.get_remote('master'),
        }
        return data

    def get_master_url(self):
        conv = self.conversation()
        return conv.get_remote('connection_string')

    def get_master_ip(self):
        conv = self.conversation()
        return conv.get_remote('master')
