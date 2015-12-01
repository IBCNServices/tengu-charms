# pylint: disable=C0111,R0201,C0301
# Source: http://gethue.com/how-to-build-hue-on-ubuntu-14-04-trusty/
from charms.reactive import when, when_not, when_file_changed
from charms.reactive import set_state
from charmhelpers.core import hookenv

import hueutils

# This file contains the reactive handlers for this charm.  These handlers
# determine when the various relations and other conditions are met so that
# Hue can be deployed.  The states used by this charm to determine this are:
#
#   * bootstrapped - This is set by the bigdata base layer once all of the
#                    library dependencies are installed.
#                    (https://github.com/juju-solutions/layer-bigdata)
#
#   * hue.installed - This is set by this charm in the code below.
#
#   * hadoop.connected - This is set by the hadoop-plugin interface layer once
#                        the plugin subordinate charm is connected to both this
#                        charm and the Hadoop core cluster.  The prefix "hadoop"
#                        in this state is determined by the name of the relation
#                        to the plugin charm in metadata.yaml.
#                        (https://github.com/juju-solutions/interface-hadoop-plugin)
#
#   * hadoop.yarn.ready - This is set by the hadoop-plugin interface layer once
#                         Yarn has reported that it is ready to run jobs.  The
#                         prefix "hadoop"in this state is determined by the name of
#                         the relationto the plugin charm in metadata.yaml.
#
#   * hadoop.hdfs.ready - This is set by the hadoop-plugin interface layer once
#                         HDFS has reported that it is ready to store data.  The
#                         prefix "hadoop"in this state is determined by the name
#                         of the relationto the plugin charm in metadata.yaml.



@when_not('hue.installed')
@when('bootstrapped')
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
def waiting(*args):
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')


@when(
    'yarn.configured',
    'hdfs.configured', # Hue is functional if these two components are connected
)
@when_not('hue.started')
def start_hue():
    hue = hueutils.Hue()
    hue.start()
    hue.open_ports()
    set_state('hue.started')
    hookenv.status_set('active', 'Ready')


@when('hue.started')
@when_not('yarn.available', 'hdfs.available')
def stop_hue():
    hookenv.status_set('maintenance', 'Stopping Hue')
    hue = hueutils.Hue()
    hue.close_ports()
    hue.stop()


@when('hue.started')
@when_file_changed('/usr/share/hue/desktop/conf/hue.ini')
def restart_hue():
    hue = hueutils.Hue()
    hue.restart()


@when(
    'hue.installed', # Hue should be installed
    'hdfs.available', # Yarn relation available
    'hadoop.hdfs.ready' # Plugin should indicate hdfs is ready
    )
@when_not('hdfs.configured')
def configure_hdfs(hdfs, hadoop):
    from jujubigdata.utils import re_edit_in_place
    hue = hueutils.Hue()
    namenode_ip = hdfs.private_address
    assert namenode_ip
    namenode = namenode_ip+":8020"
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*fs_defaultfs=hdfs://.*' : "      fs_defaultfs=hdfs://{}".format(namenode),
        r'^\s*#*\s*webhdfs_url=http://.*' : "      webhdfs_url=http://{}:50070/webhdfs/v1".format(namenode_ip),

    })
    set_state('hdfs.configured')


@when(
    'hue.installed', # Hue should be installed
    'yarn.available', # Yarn relation available
    'hadoop.yarn.ready' # Plugin should indicate yarn is ready
    )
@when_not('yarn.configured')
def configure_yarn(yarn, hadoop):
    from jujubigdata.utils import re_edit_in_place
    hue = hueutils.Hue()
    resourcemanager_ip = yarn.private_address
    assert resourcemanager_ip
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*resourcemanager_host=.*' : "      resourcemanager_host={}".format(resourcemanager_ip),
        r'^\s*#*\s*resourcemanager_port=.*' : "      resourcemanager_port=8032",
        r'^\s*#*\s*resourcemanager_api_url=http://.*' : "      resourcemanager_api_url=http://{}:8088".format(resourcemanager_ip),
        r'^\s*#*\s*proxy_api_url=http://.*' : "      proxy_api_url=http://{}:8088".format(resourcemanager_ip),
        r'^\s*#*\s*history_server_api_url=http://.*' : "      history_server_api_url=http://{}:19888".format(resourcemanager_ip),
    })
    set_state('yarn.configured')


@when(
    'hue.installed', # Hue should be installed
    'spark.available', # Spark relation available
    )
@when_not('spark.configured')
def configure_spark(spark):
    from jujubigdata.utils import re_edit_in_place
    hue = hueutils.Hue()
    livy_ip = spark.private_address
    livy_port = spark.private_address
    assert livy_ip
    assert livy_port
    livy = livy_ip + livy_port
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*server_url=http://.*' : "      server_url=http://{}".format(livy),
    })
    set_state('spark.configured')


@when('hue.installed', 'hive.available')
@when_not('hadoop.hive.configured')
def hive_relation_changed(hive):
    from jujubigdata.utils import re_edit_in_place
    hue = hueutils.Hue()
    hive_ip = hive.private_address
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*hive_server_host=localhost' : "      hive_server_host={}".format(hive_ip),
    })
    set_state('hive.configured')


@when('hue.installed', 'oozie.available')
@when_not('oozie.configured')
def oozie_relation_changed(oozie):
    from jujubigdata.utils import re_edit_in_place
    hue = hueutils.Hue()
    oozie_ip = oozie.private_address
    re_edit_in_place(hue.hue_ini, {
        r'^\s*#*\s*oozie_url=http://localhost:11000/oozie' : "      oozie_url=http://{}:11000/oozie".format(oozie_ip),
    })
    set_state('oozie.configured')
