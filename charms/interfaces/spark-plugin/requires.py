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


class SparkPluginRequires(RelationBase):
    scope = scopes.GLOBAL

    def spark_ready(self):
        return self.get_remote('spark-ready', 'false').lower() == 'true'

    @hook('{provides:spark-plugin}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.connected')

    @hook('{provides:spark-plugin}-relation-changed')
    def changed(self):
        if self.spark_ready():
            self.set_state('{relation_name}.ready')

    @hook('{provides:spark-plugin}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.connected')
        conv.remove_state('{relation_name}.ready')
