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

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class JavaProvides(RelationBase):
    scope = scopes.GLOBAL

    # convenient way to provide accessor methods
    auto_accessors = ['java-home', 'java-version']

    def java_ready(self):
        return self.get_remote('java-ready', 'false').lower() == 'true'

    @hook('{provides:java}-relation-changed')
    def changed(self):
        if self.java_ready():
            self.set_state('{relation_name}.ready')
        else:
            self.remove_state('{relation_name}.ready')

    @hook('{provides:java}-relation-departed')
    def departed(self):
        self.remove_state('{relation_name}.ready')
