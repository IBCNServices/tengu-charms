from path import Path

from charms.reactive import when
from charms.reactive import when_all
from charms.reactive import when_not_all
from charms.reactive import when_file_changed
from charms.reactive import is_state
from charms.reactive import set_state
from charms.reactive import remove_state

from charms.templating.jinja2 import render

from charms.layer.hadoop_base import get_hadoop_base
from jujubigdata.handlers import HDFS, YARN


GANGLIA_CONF_FILE = '/etc/hadoop/conf/hadoop-metrics2.properties'


@when('hadoop.installed')
@when_all('ganglia.joined', 'config.set.ganglia_metrics')
def configure_ganglia(ganglia):
    endpoints = ganglia.endpoints()
    render(
        source='hadoop-metrics2.properties.j2',
        target=GANGLIA_CONF_FILE,
        context={
            'servers': ','.join(map('{0[host]}:{0[port]}'.format, endpoints)),
        },
    )
    set_state('hadoop-ganglia.enabled')


@when('hadoop-ganglia.enabled')
@when_not_all('ganglia.joined', 'config.set.ganglia_metrics')
def disable_ganglia():
    Path(GANGLIA_CONF_FILE).remove_p()
    remove_state('hadoop-ganglia.enabled')


@when_file_changed(GANGLIA_CONF_FILE)
def ganglia_changed():
    hadoop = get_hadoop_base()
    hdfs = HDFS(hadoop)
    yarn = YARN(hadoop)
    if is_state('namenode.started'):
        hdfs.restart_namenode()
    if is_state('datanode.started'):
        hdfs.restart_datanode()
    if is_state('journalnode.started'):
        hdfs.restart_journalnode()
    if is_state('resourcemanager.started'):
        yarn.restart_resourcemanager()
    if is_state('nodemanager.started'):
        yarn.restart_nodemanager()
