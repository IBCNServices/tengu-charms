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
Callbacks for additional setup tasks.

Add any additional tasks / setup here.  If a callback is used by mutliple
charms, consider refactoring it up to the jujubigdata library.
"""

from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from jujubigdata.relations import NameNodeMaster, ResourceManagerMaster, Ganglia
from charmhelpers.core.templating import render
from functools import partial


def update_blocked_status():
    if unitdata.kv().get('charm.active', False):
        return
    rels = [
        ('HDFS', 'NameNode', NameNodeMaster()),
    ]
    missing_rel = [rel for rel, res, impl in rels if not impl.connected_units()]
    rels.append(('Yarn', 'ResourceManager', ResourceManagerMaster()))
    not_ready = [(rel, res) for rel, res, impl in rels if impl.connected_units() and not impl.is_ready()]
    missing_hosts = [rel for rel, res, impl in rels if impl.connected_units() and not impl.am_i_registered()]
    if missing_rel:
        hookenv.status_set('blocked', 'Waiting for relation to %s master%s' % (
            ' and '.join(missing_rel),
            's' if len(missing_rel) > 1 else '',
        )),
    elif not_ready:
        unready_rels, unready_ress = zip(*not_ready)
        hookenv.status_set('waiting', 'Waiting for %s to provide %s' % (
            ' and '.join(unready_rels),
            ' and '.join(unready_ress),
        ))
    elif missing_hosts:
        hookenv.status_set('waiting', 'Waiting for /etc/hosts registration on %s' % (
            ' and '.join(missing_hosts),
        ))


def update_working_status():
    if unitdata.kv().get('charm.active', False):
        hookenv.status_set('maintenance', 'Updating configuration')
        return
    yarn_connected = ResourceManagerMaster().connected_units()
    hookenv.status_set('maintenance', 'Setting up DataNode%s' % (
        ' and NodeManager' if yarn_connected else '',
    ))


def update_active_status():
    hdfs_ready = NameNodeMaster().is_ready()
    yarn_connected = ResourceManagerMaster().connected_units()
    yarn_ready = ResourceManagerMaster().is_ready()
    if hdfs_ready and (not yarn_connected or yarn_ready):
        unitdata.kv().set('charm.active', True)
        hookenv.status_set('active', 'Ready%s' % (
            '' if yarn_ready else ' (HDFS only)'
        ))
    else:
        clear_active_flag()
        update_blocked_status()


def clear_active_flag():
    unitdata.kv().set('charm.active', False)


def conf_ganglia_metrics(purgeConf=False):
    """
    Send hadoop specific metrics to a ganglia server
    """
    config = hookenv.config()
    ganglia_metrics = config['ganglia_metrics'] and not purgeConf
    ganglia_metrics_changed = ganglia_metrics != unitdata.kv().get('ganglia_metrics', False)
    unitdata.kv().set('ganglia_metrics', ganglia_metrics)
    comment = '#' if not ganglia_metrics else ''
    ganglia_host = 'UNSET_BY_JUJU' if not ganglia_metrics else Ganglia().host()
    ganglia_sink_str = comment + '*.sink.ganglia.class=org.apache.hadoop.metrics2.sink.ganglia.GangliaSink31'
    hookenv.log("Configuring ganglia sink in /etc/hadoop/conf/hadoop-metrics2.properties", level=None)
    render(
        source='hadoop-metrics2.properties.j2',
        target='/etc/hadoop/conf/hadoop-metrics2.properties',
        context={
            'ganglia_host': ganglia_host,
            'ganglia_sink_str': ganglia_sink_str,
        },
    ),
    if ganglia_metrics_changed:
        #check_call(['actions/restart-hdfs'])
        # IMPLEMENT RESTART COMPUTE SLAVE?
        hookenv.log("please manually restart compute slave hadoop components", level=None)

purge_ganglia_metrics = partial(conf_ganglia_metrics, purgeConf=True)
