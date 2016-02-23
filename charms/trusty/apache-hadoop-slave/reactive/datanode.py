from charms.reactive import when, when_not, set_state, remove_state
from charms.hadoop import get_hadoop_base
from jujubigdata.handlers import HDFS
from jujubigdata import utils


@when('namenode.ready')
@when_not('datanode.started')
def start_datanode(namenode):
    hadoop = get_hadoop_base()
    hdfs = HDFS(hadoop)
    hdfs.configure_datanode(namenode.namenodes()[0], namenode.port())
    utils.install_ssh_key('hdfs', namenode.ssh_key())
    utils.update_kv_hosts(namenode.hosts_map())
    utils.manage_etc_hosts()
    hdfs.start_datanode()
    hadoop.open_ports('datanode')
    set_state('datanode.started')


@when('datanode.started')
@when_not('namenode.ready')
def stop_datanode():
    hadoop = get_hadoop_base()
    hdfs = HDFS(hadoop)
    hdfs.stop_datanode()
    hadoop.close_ports('datanode')
    remove_state('datanode.started')
