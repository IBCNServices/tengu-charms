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


class SparkProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:spark}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{provides:spark}-relation-departed')
    def departed(self):
        conv = self.conversation()
        if len(conv.units) <= 1: # last remaining unit departing
            conv.remove_state('{relation_name}.joined')

    def set_spark_started(self):
        self.set_remote(data={
            'spark_started': True,
        })

    def clear_spark_started(self):
        self.set_remote('spark_started', False)

    def send_rest_port(self, rest_port):
        conv = self.conversation()
        conv.set_remote(data={
            'rest_port': rest_port,
        })

    def send_master_info(self, connection_string, master):
        conv = self.conversation()
        conv.set_remote(data={
            'connection_string': connection_string,
            'master': master,
        })
