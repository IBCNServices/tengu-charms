# pylint: disable=C0111,R0201,C0301
# Source: http://gethue.com/how-to-build-hue-on-ubuntu-14-04-trusty/
from charms.reactive import when, when_not
from charms.reactive import set_state
from charmhelpers.core import hookenv

import hueutils

@when_not('hue.installed')
def install_hue():
    hue = hueutils.Hue()
    if hue.verify_resources(): # will set blocked state if fetching failed
        hookenv.status_set('maintenance', 'Installing Hue')
        hue.install()
        set_state('hue.installed')


@when('hue.installed')
@when_not('hadoop.connected')
def blocked():
    hookenv.status_set('blocked', 'Waiting for relation to Hadoop')


@when('hue.installed', 'hadoop.connected')
@when_not('hadoop.yarn.ready', 'hadoop.hdfs.ready')
@when_not('hue.started')
def waiting():
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')


@when('hue.installed', 'hadoop.yarn.ready', 'hadoop.hdfs.ready')
def start_hue():
    hookenv.status_set('maintenance', 'Setting up Apache Hue')
    hue = hueutils.Hue()
    hue.start()
    hue.open_ports()
    set_state('hue.started')
    hookenv.status_set('active', 'Ready')


@when('hue.started')
@when_not('hadoop.yarn.ready', 'hadoop.hdfs.ready')
def stop_hue():
    hookenv.status_set('maintenance', 'Stopping Hue')
    hue = hueutils.Hue()
    hue.close_ports()
    hue.stop()


@when('hadoop.hdfs.ready')
@when_not('hadoop.hdfs.configured')
def namenode_relation_changed(hdfs):
    from jujubigdata.utils import re_edit_in_place

    set_state('hadoop.connected')

    hue = hueutils.Hue()
    namenode_ip = hdfs.private_address
    assert(namenode_ip)
    namenode = namenode_ip+":8020"
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*fs_defaultfs=hdfs://.*' : "      fs_defaultfs=hdfs://{}".format(namenode),
        r'^\s*#*\s*webhdfs_url=http://.*' : "      webhdfs_url=http://{}:50070/webhdfs/v1".format(namenode_ip),

    })
    set_state('hadoop.hdfs.configured')
    hue.restart()


@when('hadoop.yarn.ready')
@when_not('hadoop.yarn.configured')
def yarn_relation_changed(yarn):
    from jujubigdata.utils import re_edit_in_place
    set_state('yarn.connected')
    hue = hueutils.Hue()
    resourcemanager_ip = yarn.private_address
    assert(resourcemanager_ip)
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*resourcemanager_host=.*' : "      resourcemanager_host={}".format(resourcemanager_ip),
        r'^\s*#*\s*resourcemanager_port=.*' : "      resourcemanager_port=8032",
        r'^\s*#*\s*resourcemanager_api_url=http://.*' : "      resourcemanager_api_url=http://{}:8088".format(resourcemanager_ip),
        r'^\s*#*\s*proxy_api_url=http://.*' : "      proxy_api_url=http://{}:8088".format(resourcemanager_ip),
        r'^\s*#*\s*history_server_api_url=http://.*' : "      history_server_api_url=http://{}:19888".format(resourcemanager_ip),
    })
    set_state('hadoop.yarn.configured')
    hue.restart()


@when('hadoop.hive.available')
@when_not('hadoop.hive.configured')
def hive_relation_changed(hive):
    from jujubigdata.utils import re_edit_in_place
    set_state('hive.connected')
    hue = hueutils.Hue()
    hive_ip = hive.private_address
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*hive_server_host=localhost' : "      hive_server_host={}".format(hive_ip),
    })
    set_state('hadoop.hive.configured')
    hue.restart()


@when('hadoop.oozie.available')
@when_not('hadoop.oozie.configured')
def oozie_relation_changed(oozie):
    from jujubigdata.utils import re_edit_in_place
    set_state('oozie.connected')
    hue = hueutils.Hue()
    oozie_ip = oozie.private_address
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*oozie_url=http://localhost:11000/oozie' : "      oozie_url=http://{}:11000/oozie".format(oozie_ip),
    })
    set_state('hadoop.oozie.configured')
    hue.restart()
