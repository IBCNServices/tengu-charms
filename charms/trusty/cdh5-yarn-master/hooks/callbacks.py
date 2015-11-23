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
from jujubigdata.relations import NameNode, NodeManager, Ganglia
from charmhelpers.core.templating import render 
from functools import partial
from subprocess import check_call


def update_blocked_status():
    if unitdata.kv().get('charm.active', False):
        return
    if NameNode().connected_units():
        hookenv.status_set('waiting', 'Waiting for HDFS master to provide NameNode'),
    else:
        hookenv.status_set('blocked', 'Waiting for relation to HDFS master'),


def update_working_status():
    if unitdata.kv().get('charm.active', False):
        hookenv.status_set('maintenance', 'Updating configuration')
        return
    hookenv.status_set('maintenance', 'Setting up Yarn master')


def update_active_status():
    nodemanager = NodeManager()
    if nodemanager.is_ready():
        hookenv.status_set('active', 'Ready (%s NodeManagers)' % len(nodemanager.filtered_data()))
        unitdata.kv().set('charm.active', True)
    elif nodemanager.connected_units():
        hookenv.status_set('waiting', 'Waiting for compute slaves to provide NodeManagers')
    else:
        hookenv.status_set('blocked', 'Waiting for relation to compute slaves')


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
        check_call(['actions/restart-yarn'])


purge_ganglia_metrics = partial(conf_ganglia_metrics, purgeConf=True)
