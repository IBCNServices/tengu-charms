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


class DataNodeProvides(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['port', 'webhdfs-port', 'ssh-key']

    def set_local_spec(self, spec):
        """
        Set the local spec.

        Should be called after ``{relation_name}.joined``.
        """
        conv = self.conversation()
        conv.set_local('spec', json.dumps(spec))

    def local_hostname(self):
        return hookenv.local_unit().replace('/', '-')

    def local_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_local('spec', 'null'))

    def remote_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('spec', 'null'))

    def namenodes(self):
        """
        Returns a list of the NameNode host names.
        """
        conv = self.conversation()
        return json.loads(conv.get_remote('namenodes', '[]'))

    def hosts_map(self):
        """
        Return a mapping of IPs to host names suitable for use with
        `jujubigdata.utils.update_etc_hosts`.

        This will contain the IPs of the NameNode host names, as well as all
        other DataNode host names, to ensure that they are resolvable.
        """
        conv = self.conversation()
        return json.loads(conv.get_remote('etc_hosts', '{}'))

    @hook('{provides:dfs-slave}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{provides:dfs-slave}-relation-changed')
    def changed(self):
        hookenv.log('Data: {}'.format({
            'local_spec': self.local_spec(),
            'remote_spec': self.remote_spec(),
            'namenodes': self.namenodes(),
            'port': self.port(),
            'webhdfs_port': self.webhdfs_port(),
            'hosts_map': self.hosts_map(),
            'local_hostname': self.local_hostname(),
        }))
        conv = self.conversation()
        available = all([
            self.remote_spec() is not None,
            self.hosts_map(),
            self.namenodes(),
            self.port(),
            self.webhdfs_port(),
            self.ssh_key()])
        spec_mismatch = available and not self._spec_match()
        visible = self.local_hostname() in self.hosts_map().values()
        ready = available and visible

        conv.toggle_state('{relation_name}.spec.mismatch', spec_mismatch)
        conv.toggle_state('{relation_name}.ready', ready and not spec_mismatch)

        hookenv.log('States: {}'.format(set(get_states().keys())))

    @hook('{provides:dfs-slave}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.joined')
        conv.remove_state('{relation_name}.spec.mismatch')
        conv.remove_state('{relation_name}.ready')

    def _spec_match(self):
        datanode_spec = self.local_spec()
        namenode_spec = self.remote_spec()
        if None in (datanode_spec, namenode_spec):
            return False
        for key, value in datanode_spec.items():
            if value != namenode_spec.get(key):
                return False
        return True
