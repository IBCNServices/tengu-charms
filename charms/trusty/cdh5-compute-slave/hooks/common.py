#!/usr/bin/env python
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
"""
Common implementation for all hooks.
"""

import jujuresources
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.core import charmframework


def bootstrap_resources():
    """
    Install required resources defined in resources.yaml
    """
    if unitdata.kv().get('charm.bootstrapped', False):
        return True
    hookenv.status_set('maintenance', 'Installing base resources')
    mirror_url = jujuresources.config_get('resources_mirror')
    if not jujuresources.fetch(mirror_url=mirror_url):
        missing = jujuresources.invalid()
        hookenv.status_set('blocked', 'Unable to fetch required resource%s: %s' % (
            's' if len(missing) > 1 else '',
            ', '.join(missing),
        ))
        return False
    jujuresources.install(['pathlib', 'jujubigdata'])
    unitdata.kv().set('charm.bootstrapped', True)
    return True


def manage():
    if not bootstrap_resources():
        # defer until resources are available, since jujubigdata, and thus the
        # classes needed for the requires blocks, (will be) managed by jujuresources
        return

    import jujubigdata
    import callbacks

    # list of keys required to be in the dist.yaml
    slave_reqs = ['vendor', 'hadoop_version', 'packages', 'groups', 'users',
                  'dirs', 'ports']
    dist_config = jujubigdata.utils.DistConfig(filename='dist.yaml',
                                               required_keys=slave_reqs)
    hadoop = jujubigdata.handlers.HadoopBase(dist_config)
    hdfs = jujubigdata.handlers.HDFS(hadoop)
    hdfs_relation = jujubigdata.relations.NameNodeMaster(spec=hadoop.spec)
    yarn = jujubigdata.handlers.YARN(hadoop)
    yarn_relation = jujubigdata.relations.ResourceManagerMaster(spec=hadoop.spec)
    manager = charmframework.Manager([
        {
            'name': 'hadoop-base',
            'requires': [
                hadoop.verify_conditional_resources,
            ],
            'callbacks': [
                hadoop.install,
                callbacks.update_blocked_status,
            ],
        },
        {
            'name': 'datanode',
            'provides': [
                jujubigdata.relations.DataNode(),
            ],
            'requires': [
                hadoop.is_installed,
                hdfs_relation,
                hdfs_relation.am_i_registered,
            ],
            'callbacks': [
                callbacks.update_working_status,
                hdfs_relation.register_provided_hosts,
                jujubigdata.utils.manage_etc_hosts,
                hdfs_relation.install_ssh_keys,
                hdfs.configure_datanode,
                hdfs.start_datanode,
                charmframework.helpers.open_ports(
                    dist_config.exposed_ports('compute-slave-hdfs')),
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                charmframework.helpers.close_ports(
                    dist_config.exposed_ports('compute-slave-hdfs')),
                hdfs.stop_datanode,
                callbacks.update_blocked_status,
            ],
        },
        {
            'name': 'nodemanager',
            'provides': [
                jujubigdata.relations.NodeManager(),
            ],
            'requires': [
                hadoop.is_installed,
                yarn_relation,
                yarn_relation.am_i_registered,
            ],
            'callbacks': [
                callbacks.update_working_status,
                yarn_relation.register_provided_hosts,
                jujubigdata.utils.manage_etc_hosts,
                yarn_relation.install_ssh_keys,
                yarn.configure_nodemanager,
                yarn.start_nodemanager,
                charmframework.helpers.open_ports(
                    dist_config.exposed_ports('compute-slave-yarn')),
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                charmframework.helpers.close_ports(
                    dist_config.exposed_ports('compute-slave-yarn')),
                yarn.stop_nodemanager,
                callbacks.update_active_status,  # might still be active if HDFS-only
            ],
        },
        {
            'name': 'ganglia',
            'requires': [
                hadoop.is_installed,
                jujubigdata.relations.Ganglia,
            ],
            'callbacks': [
                callbacks.conf_ganglia_metrics,
            ],
            'cleanup': [
                callbacks.purge_ganglia_metrics
            ],
        },

    ])
    manager.manage()


if __name__ == '__main__':
    manage()
