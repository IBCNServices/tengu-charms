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


class DFSRequires(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['port', 'webhdfs-port']

    def set_local_spec(self, spec):
        """
        Set the local spec.

        Should be called after ``{relation_name}.joined``.
        """
        conv = self.conversation()
        conv.set_local('spec', json.dumps(spec))

    def remote_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_remote('spec', 'null'))

    def local_spec(self):
        conv = self.conversation()
        return json.loads(conv.get_local('spec', 'null'))

    def hdfs_ready(self):
        conv = self.conversation()
        return conv.get_remote('has_slave', '').lower() == 'true'

    def namenodes(self):
        """
        Returns a list of the NameNode host names.
        """
        conv = self.conversation()
        namenodes = json.loads(conv.get_remote('namenodes', '[]'))
        if self.hdfs_ready() and not namenodes:
            # temporary work-around for connecting with old, non-layered charms
            namenodes = [unit.replace('/', '-') for unit in conv.units]
        return namenodes

    def hosts_map(self):
        """
        Return a mapping of IPs to host names suitable for use with
        `jujubigdata.utils.update_etc_hosts`.

        This will contain the IPs of the NameNode host names, to ensure that
        they are resolvable.
        """
        conv = self.conversation()
        return json.loads(conv.get_remote('etc_hosts', '{}'))

    @hook('{requires:dfs}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{requires:dfs}-relation-changed')
    def changed(self):
        conv = self.conversation()
        hookenv.log('Data: {}'.format({
            'remote_spec': self.remote_spec(),
            'local_spec': self.local_spec(),
            'hosts-map': self.hosts_map(),
            'namenodes': self.namenodes(),
            'port': self.port(),
            'webhdfs_port': self.webhdfs_port(),
        }))
        available = all([
            self.remote_spec() is not None,
            self.hosts_map(),
            self.namenodes(),
            self.port(),
            self.webhdfs_port()])
        spec_mismatch = available and not self._spec_match()
        ready = available and self.hdfs_ready()

        conv.toggle_state('{relation_name}.spec.mismatch', spec_mismatch)
        conv.toggle_state('{relation_name}.ready', ready and not spec_mismatch)

        hookenv.log('States: {}'.format(set(get_states().keys())))

    @hook('{requires:dfs}-relation-departed')
    def departed(self):
        self.remove_state('{relation_name}.joined')
        self.remove_state('{relation_name}.spec.mismatch')
        self.remove_state('{relation_name}.ready')

    def _spec_match(self):
        local_spec = self.local_spec()
        remote_spec = self.remote_spec()
        if None in (local_spec, remote_spec):
            return False
        for key, value in local_spec.items():
            if value != remote_spec.get(key):
                return False
        return True
