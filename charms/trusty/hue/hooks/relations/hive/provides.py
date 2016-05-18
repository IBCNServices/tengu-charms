# pylint: disable=too-many-arguments
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


class HiveProvides(RelationBase):
    scope = scopes.GLOBAL

    auto_accessors = ['hostname', 'port']

    @hook('{provides:hive}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{provides:hive}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.joined')

    def set_ready(self):
        self.set_remote(data={
            'ready': True,
        })

    def clear_ready(self):
        self.set_remote('ready', False)

    def send_port(self, port):
        conv = self.conversation()
        conv.set_remote(data={
            'port': port,
        })
