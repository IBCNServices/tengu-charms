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


class HadoopPluginProvides(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['version',
                      'hdfs-port',
                      'yarn-port',
                      'yarn-hs-http-port',
                      'yarn-hs-ipc-port']

    def installed(self):
        installed = self.get_remote('installed', 'false').lower() == 'true'
        return self.version() and installed

    def hdfs_ready(self):
        available = all([self.namenodes(), self.hdfs_port()])
        ready = self.get_remote('hdfs-ready', 'false').lower() == 'true'
        return available and ready

    def yarn_ready(self):
        available = all([self.resourcemanagers(), self.yarn_port(),
                         self.yarn_hs_http_port(), self.yarn_hs_ipc_port()])
        ready = self.get_remote('yarn-ready', 'false').lower() == 'true'
        return available and ready

    def namenodes(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('hdfs-namenodes', '[]'))

    def resourcemanagers(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('yarn-resourcemanagers', '[]'))

    @hook('{provides:hadoop-plugin}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.related')

    @hook('{provides:hadoop-plugin}-relation-changed')
    def changed(self):
        conv = self.conversation()
        if self.installed():
            conv.set_state('{relation_name}.installed')
        if self.installed() and self.hdfs_ready():
            conv.set_state('{relation_name}.hdfs.ready')
        if self.installed() and self.yarn_ready():
            conv.set_state('{relation_name}.yarn.ready')
        if self.installed() and self.hdfs_ready() and self.yarn_ready():
            conv.set_state('{relation_name}.ready')

    @hook('{provides:hadoop-plugin}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.related')
        conv.remove_state('{relation_name}.installed')
        conv.remove_state('{relation_name}.ready')
        conv.remove_state('{relation_name}.hdfs.ready')
        conv.remove_state('{relation_name}.yarn.ready')
