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


class BenchmarkProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:benchmark}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{provides:benchmark}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.joined')

    def register(self, *benchmarks):
        """
        Register one or more benchmarks.

        :param benchmarks: One or more benchmark names, or a list
            containing one or more benchmark names.
        """
        if len(benchmarks) == 1 and isinstance(benchmarks[0], (list, tuple)):
            benchmarks = benchmarks[0]
        conv = self.conversation()
        conv.set_remote('benchmarks', ','.join(benchmarks))
