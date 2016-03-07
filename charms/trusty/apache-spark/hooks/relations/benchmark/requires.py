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


class BenchmarkRequires(RelationBase):
    scope = scopes.SERVICE

    def registered(self):
        """
        Returns a dict mapping each service name to a list of the benchmarks
        that service has registered.
        """
        result = {}
        for conv in self.conversations():
            service = conv.scope
            benchmarks = conv.get_remote('benchmarks', '').split(',')
            result[service] = benchmarks
        return result

    @hook('{requires:benchmark}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.related')

    @hook('{requires:benchmark}-relation-changed')
    def changed(self):
        conv = self.conversation()
        benchmarks = conv.get_remote('benchmarks', '').split(',')

        conv.toggle_state('{relation_name}.registered', benchmarks)

    @hook('{requires:benchmark}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.related')
        conv.remove_state('{relation_name}.registered')
