from charms.reactive import when, when_not, when_file_changed
from charms.reactive import set_state, remove_state
from charms.reactive.bus import get_states
from charmhelpers.core import hookenv
from charms.hue import Hue
from charms.layer.hadoop_client import get_dist_config


@when_not('hadoop.ready')
def missing_hadoop():
    hookenv.status_set('blocked', 'Waiting for relation to Hadoop Plugin')


@when('hadoop.ready')
@when_not('hue.installed')
def install_hue(hadoop):
    hue = Hue(get_dist_config())
    if hue.verify_resources():
        hookenv.status_set('maintenance', 'Installing Hue')
        hue.install()
        set_state('hue.installed')


@when('hue.installed', 'hadoop.ready')
@when_not('hue.configured')
def configure_hue(hadoop):
    namenodes = hadoop.namenodes()
    resmngmrs = hadoop.resourcemanagers()
    hdfs_port = hadoop.hdfs_port()
    yarn_port = hadoop.yarn_port()
    hookenv.status_set('maintenance', 'Setting up Hue')
    hue = Hue(get_dist_config())
    hue.setup_hue(namenodes, resmngmrs, hdfs_port,
                  yarn_port, yarn_http, yarn_ipcp)
    set_state('hue.configured')


@when('hue.installed', 'hadoop.ready', 'hue.configured')
@when_not('hue.started')
def start_hue(hadoop):
    hookenv.status_set('maintenance', 'Setting up Hue')
    hue = Hue(get_dist_config())
    hue.open_ports()
    hue.start()
    set_state('hue.started')

if 'hue.started' in get_states():
    @when_file_changed('/etc/hue/conf/hue.ini')
    def restart_hue():
        # Can't seem to mix @when_file_changed and @when('hue.started')
        hue = Hue(get_dist_config())
        hue.restart()


@when('hue.started', 'hadoop.ready')
def check_relations(*args):
    hue = Hue(get_dist_config())
    hue.check_relations()


@when('hue.started', 'hive.ready')
@when_not('hive.configured')
def configure_hive(hive):
    hookenv.status_set('maintenance', 'Configuring Hue for Hive')
    hive_host = hive.get_private_ip()
    hive_port = hive.get_port()
    hue = Hue(get_dist_config())
    hue.configure_hive(hive_host, hive_port)
    hue.update_apps()
    hue.restart()
    set_state('hive.configured')


@when('hue.started', 'zookeeper.ready')
@when_not('zookeeper.configured')
def configure_zookeeper(zks):
    hookenv.status_set('maintenance', 'Configuring Hue for Zookeeper')
    hue = Hue(get_dist_config())
    hue.configure_zookeeper(zks.zookeepers())
    hue.update_apps()
    hue.restart()
    set_state('zookeeper.configured')


@when('hue.started', 'spark.ready')
@when_not('spark.configured')
def configure_spark(spark):
    hookenv.status_set('maintenance', 'Configuring Hue for Spark')
    spark_host = spark.get_private_ip()
    spark_rest_port = spark.get_rest_port()
    hue = Hue(get_dist_config())
    hue.configure_spark(spark_host, spark_rest_port)
    hue.update_apps()
    hue.restart()
    set_state('spark.configured')


@when('hue.started', 'oozie.ready')
@when_not('oozie.configured')
def configure_oozie(oozie):
    oozie_host = oozie.private_address
    oozie_port = oozie.port
    hue = Hue(get_dist_config())
    hue.configure_oozie(oozie_host, oozie_port)
    hue.update_apps()
    hue.restart()
    set_state('oozie.configured')


@when('hue.started', 'hive.configured')
@when_not('hive.joined')
def depart_hive():
    hookenv.status_set('maintenance', 'Disconnecting Hive from Hue')
    remove_state('hive.configured')
    hue = Hue(get_dist_config())
    hue.update_apps()
    hue.restart()


@when('hue.started', 'zookeeper.configured')
@when_not('zookeeper.joined')
def depart_zookeeper():
    hookenv.status_set('maintenance', 'Disconnecting Zookeeper from Hue')
    remove_state('zookeeper.configured')
    hue = Hue(get_dist_config())
    hue.update_apps()
    hue.restart()


@when('hue.started', 'oozie.configured')
@when_not('oozie.joined')
def depart_oozie():
    hookenv.status_set('maintenance', 'Disconnecting Oozie from Hue')
    remove_state('oozie.configured')
    hue = Hue(get_dist_config())
    hue.update_apps()
    hue.restart()


@when('hue.started', 'spark.configured')
@when_not('spark.joined')
def depart_spark():
    hookenv.status_set('maintenance', 'Disconnecting Spark from Hue')
    remove_state('spark.configured')
    hue = Hue(get_dist_config())
    hue.update_apps()
    hue.restart()


@when('hue.started')
@when_not('hadoop.ready')
def stop_hue():
    hue = Hue(get_dist_config())
    hue.stop()
    remove_state('hue.started')
    hookenv.status_set('blocked', 'Waiting for Hadoop connection')
