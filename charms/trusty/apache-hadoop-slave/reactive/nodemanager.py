from charms.reactive import when, when_not, set_state, remove_state
from charms.hadoop import get_hadoop_base
from jujubigdata.handlers import YARN
from jujubigdata import utils


@when('resourcemanager.ready')
@when_not('nodemanager.started')
def start_nodemanager(resourcemanager):
    hadoop = get_hadoop_base()
    yarn = YARN(hadoop)
    yarn.configure_nodemanager(resourcemanager.resourcemanagers()[0], resourcemanager.port(),
                               resourcemanager.hs_http(), resourcemanager.hs_ipc())
    utils.install_ssh_key('yarn', resourcemanager.ssh_key())
    utils.update_kv_hosts(resourcemanager.hosts_map())
    utils.manage_etc_hosts()
    yarn.start_nodemanager()
    hadoop.open_ports('nodemanager')
    set_state('nodemanager.started')


@when('nodemanager.started')
@when_not('resourcemanager.ready')
def stop_nodemanager():
    hadoop = get_hadoop_base()
    yarn = YARN(hadoop)
    yarn.stop_nodemanager()
    hadoop.close_ports('nodemanager')
    remove_state('nodemanager.started')
