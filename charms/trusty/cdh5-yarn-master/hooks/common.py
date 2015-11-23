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
    Attempt to load and install resources defined in resources.yaml
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
    yarn_reqs = ['vendor', 'hadoop_version', 'packages', 'groups',
                 'users', 'dirs', 'ports']
    dist_config = jujubigdata.utils.DistConfig(filename='dist.yaml',
                                               required_keys=yarn_reqs)
    hadoop = jujubigdata.handlers.HadoopBase(dist_config)
    yarn = jujubigdata.handlers.YARN(hadoop)
    hdfs = jujubigdata.handlers.HDFS(hadoop)
    port = dist_config.port('resourcemanager')
    hs_http = dist_config.port('jh_webapp_http')
    hs_ipc = dist_config.port('jobhistory')
    nodemanagers = jujubigdata.relations.ResourceManagerMaster(
        spec=hadoop.spec, port=port,
        historyserver_http=hs_http, historyserver_ipc=hs_ipc)
    clients = jujubigdata.relations.ResourceManager(
        spec=hadoop.spec, port=port,
        historyserver_http=hs_http, historyserver_ipc=hs_ipc)
    namenode = jujubigdata.relations.NameNode(spec=hadoop.client_spec)
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
            'name': 'yarn-master',
            'provides': [
                nodemanagers,
                clients,
            ],
            'requires': [
                hadoop.is_installed,
                namenode,
                jujubigdata.relations.NodeManager(optional=True),
            ],
            'callbacks': [
                # These callbacks will be executed once the Hadoop base packages
                # are installed and HDFS is available.  New items can be added
                # to the end of this list and to hooks/callbacks.py to extend
                # the functionality of this charm.
                callbacks.update_working_status,
                nodemanagers.register_connected_hosts,
                clients.register_connected_hosts,
                namenode.register_provided_hosts,
                jujubigdata.utils.manage_etc_hosts,
                hdfs.configure_client,
                yarn.configure_resourcemanager,
                yarn.configure_jobhistory,
                yarn.register_slaves,
                yarn.start_resourcemanager,
                yarn.start_jobhistory,
                charmframework.helpers.open_ports(dist_config.exposed_ports('yarn-master')),
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                charmframework.helpers.close_ports(dist_config.exposed_ports('yarn-master')),
                yarn.stop_resourcemanager,
                yarn.stop_jobhistory,
                callbacks.update_blocked_status,
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
                callbacks.purge_ganglia_metrics,
            ],

        },

    ])
    manager.manage()


if __name__ == '__main__':
    manage()
