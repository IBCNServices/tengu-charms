from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state
from charmhelpers.core import hookenv


# This file contains the reactive handlers for this charm.  These handlers
# determine when the various relations and other conditions are met so that
# Spark can be deployed.  The states used by this charm to determine this are:
#
#   * bootstrapped - This is set by the bigdata base layer once all of the
#                    library dependencies are installed.
#                    (https://github.com/juju-solutions/layer-bigdata)
#
#   * spark.installed - This is set by this charm in the code below.
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
#


def dist_config():
    from jujubigdata.utils import DistConfig  # no available until after bootstrap
    if not getattr(dist_config, 'value', None):
        dist_config.value = DistConfig(filename='dist.yaml',
                                       required_keys=['vendor', 'packages',
                                                      'dirs', 'ports'])
    return dist_config.value


@when('bootstrapped')
@when_not('hadoop.connected')
def blocked():
    hookenv.status_set('blocked', 'Waiting for relation to Hadoop')


@when('bootstrapped')
@when('hadoop.connected')
@when_not('hadoop.ready')
def waiting(hadoop):
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')


# TODO: support standalone mode when Yarn not connected
@when('bootstrapped')
@when('hadoop.ready')
@when_not('spark.installed')
def install_spark(hadoop):
    from charms.spark import Spark  # in lib/charms; not available until after bootstrap

    dist = dist_config()
    spark = Spark(dist)
    if spark.verify_resources():
        hookenv.status_set('maintenance', 'Installing Apache Spark')
        dist.add_dirs()
        dist.add_packages()
        spark.install()
        set_state('spark.installed')


@when('spark.installed', 'hadoop.ready')
@when_not('spark.started')
def start_spark(hadoop):
    from charms.spark import Spark  # in lib/charms; not available until after bootstrap

    hookenv.status_set('maintenance', 'Setting up Apache Spark')
    spark = Spark(dist_config())
    spark.setup_spark_config()
    spark.configure()
    spark.start()
    spark.open_ports()
    set_state('spark.started')
    hookenv.status_set('active', 'Ready')


@when('spark.started')
@when_not('hadoop.ready')
def stop_spark():
    from charms.spark import Spark  # in lib/charms; not available until after bootstrap

    hookenv.status_set('maintenance', 'Stopping Apache Spark')
    spark = Spark(dist_config())
    spark.close_ports()
    spark.stop()
    remove_state('spark.started')
