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
from charms.reactive.bus import get_states

from charmhelpers.core import hookenv


class NodeManagerProvides(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['port', 'historyserver_http', 'historyserver_ipc', 'ssh-key']

    def set_local_spec(self, spec):
        """
        Set the local spec.

        Should be called after ``{relation_name}.related``.
        """
        conv = self.conversation()
        conv.set_local('spec', json.dumps(spec))

    def local_hostname(self):
        return hookenv.local_unit().replace('/', '-')

    def local_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_local('spec', '{}'))

    def remote_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('spec', '{}'))

    def resourcemanagers(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('resourcemanagers', '[]'))

    def hosts_map(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('etc_hosts', '{}'))

    def hs_http(self):
        return self.historyserver_http()

    def hs_ipc(self):
        return self.historyserver_ipc()

    @hook('{provides:mapred-slave}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.related')

    @hook('{provides:mapred-slave}-relation-changed')
    def changed(self):
        hookenv.log('Data: {}'.format({
            'local_spec': self.local_spec(),
            'remote_spec': self.remote_spec(),
            'resourcemanagers': self.resourcemanagers(),
            'port': self.port(),
            'hs_http': self.hs_http(),
            'hs_ipc': self.hs_ipc(),
            'hosts_map': self.hosts_map(),
            'local_hostname': self.local_hostname(),
        }))
        conv = self.conversation()
        available = all([
            self.remote_spec() is not None,
            self.hosts_map(),
            self.resourcemanagers(),
            self.port(),
            self.hs_http(),
            self.hs_ipc(),
            self.ssh_key()])
        spec_matches = self._spec_match()
        visible = self.local_hostname() in self.hosts_map().values()

        conv.toggle_state('{relation_name}.spec.mismatch', available and not spec_matches)
        conv.toggle_state('{relation_name}.ready', available and spec_matches and visible)

        hookenv.log('States: {}'.format(get_states().keys()))

    @hook('{provides:mapred-slave}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.related')
        conv.remove_state('{relation_name}.spec.mismatch')
        conv.remove_state('{relation_name}.ready')

    def _spec_match(self):
        nodemanager_spec = self.local_spec()
        resourcemanager_spec = self.remote_spec()
        if None in (nodemanager_spec, resourcemanager_spec):
            return False
        for key, value in nodemanager_spec.items():
            if value != resourcemanager_spec.get(key):
                return False
        return True
