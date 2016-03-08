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

import json
from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes


class HadoopPluginRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:hadoop-plugin}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.related')

    @hook('{requires:hadoop-plugin}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.related')

    def set_installed(self, version):
        self.set_remote(data={
            'installed': True,
            'version': version,
        })

    def set_hdfs_ready(self, namenodes, port):
        conv = self.conversation()
        conv.set_remote(data={
            'hdfs-ready': True,
            'hdfs-namenodes': json.dumps(namenodes),
            'hdfs-port': port,
        })

    def clear_hdfs_ready(self):
        self.set_remote('hdfs-ready', False)

    def set_yarn_ready(self, hosts, port, hs_http_port, hs_ipc_port):
        conv = self.conversation()
        conv.set_remote(data={
            'yarn-ready': True,
            'yarn-resourcemanagers': json.dumps(hosts),
            'yarn-port': port,
            'yarn-hs-http-port': hs_http_port,
            'yarn-hs-ipc-port': hs_ipc_port,
        })

    def clear_yarn_ready(self):
        self.set_remote('yarn-ready', False)
