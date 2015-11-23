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
    master_reqs = ['vendor', 'hadoop_version', 'packages', 'groups', 'users',
                   'dirs', 'ports']
    dist_config = jujubigdata.utils.DistConfig(filename='dist.yaml',
                                               required_keys=master_reqs)
    hadoop = jujubigdata.handlers.HadoopBase(dist_config)
    hdfs = jujubigdata.handlers.HDFS(hadoop)
    hdfs_port = dist_config.port('namenode')
    webhdfs_port = dist_config.port('nn_webapp_http')
    secondary = jujubigdata.relations.NameNodeMaster(spec=hadoop.spec, port=hdfs_port, webhdfs_port=webhdfs_port,
                                                     relation_name='secondary')
    datanodes = jujubigdata.relations.NameNodeMaster(spec=hadoop.spec, port=hdfs_port, webhdfs_port=webhdfs_port)
    clients = jujubigdata.relations.NameNode(spec=hadoop.spec, port=hdfs_port, webhdfs_port=webhdfs_port)
    manager = charmframework.Manager([
        {
            'name': 'hadoop-base',
            'requires': [
                hadoop.verify_conditional_resources,
            ],
            'callbacks': [
                hadoop.install,
            ],
        },
        {
            'name': 'hdfs-master',
            'provides': [
                secondary,
                datanodes,
                clients,
            ],
            'requires': [
                hadoop.is_installed,
                jujubigdata.relations.DataNode(optional=True),
                jujubigdata.relations.SecondaryNameNode(optional=True),
            ],
            'callbacks': [
                # These callbacks will be executed once the Hadoop base packages
                # are installed.  New items can be added to the end of this list
                # and to hooks/callbacks.py to extend the functionality of this
                # charm.
                callbacks.update_working_status,
                datanodes.register_connected_hosts,
                secondary.register_connected_hosts,
                clients.register_connected_hosts,
                jujubigdata.utils.manage_etc_hosts,
                hdfs.configure_namenode,
                hdfs.register_slaves,
                hdfs.format_namenode,
                hdfs.start_namenode,
                hdfs.create_hdfs_dirs,
                charmframework.helpers.open_ports(dist_config.exposed_ports('hdfs-master')),
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                charmframework.helpers.close_ports(dist_config.exposed_ports('hdfs-master')),
                hdfs.stop_namenode,
                callbacks.update_active_status,
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
