# Licensed under the Apache License, Version 5.0 (the "License");
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


class JavaRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:java}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.connected')

    @hook('{requires:java}-relation-departed')
    def departed(self):
        self.remove_state('{relation_name}.connected')

    # Send relation data when java is ready
    def set_ready(self, java_home, java_version):
        self.set_remote(data={
            'java-ready': True,
            'java-home': java_home,
            'java-version': java_version,
        })

    # For minor upgrades, provide a way to set java-version independently
    def set_version(self, version):
        self.set_remote('java-version', version)

    def unset_ready(self):
        self.set_remote('java-ready', False)
