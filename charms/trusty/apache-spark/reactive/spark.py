# pylint: disable=unused-argument
from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state
from charmhelpers.core import hookenv
from charms.spark import Spark
from charms.hadoop import get_dist_config


# This file contains the reactive handlers for this charm.  These handlers
# determine when the various relations and other conditions are met so that
# Spark can be deployed.  The states used by this charm to determine this are:
#
#   * spark.installed - This is set by this charm in the code below.
#
#   * hadoop.related - This is set by the hadoop-plugin interface layer once
#                        the plugin subordinate charm is connected to both this
#                        charm and the Hadoop core cluster.  The prefix "hadoop"
#                        in this state is determined by the name of the relation
#                        to the plugin charm in metadata.yaml.
#                        (https://github.com/juju-solutions/interface-hadoop-plugin)
#
#   * hadoop.ready - This is set by the hadoop-plugin interface layer once
#                         Yarn & HDFS have reported that ready.  The
#                         prefix "hadoop" in this state is determined by the name of
#                         the relationto the plugin charm in metadata.yaml.
#

@when_not('hadoop.related')
def report_blocked():
    hookenv.status_set('blocked', 'Waiting for relation to Hadoop Plugin')


@when('hadoop.related')
@when_not('hadoop.ready')
def report_waiting(hadoop):
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')


# TODO: support standalone mode when Yarn not connected
@when('hadoop.ready')
@when_not('spark.installed')
def install_spark(hadoop):

    dist = get_dist_config()
    spark = Spark(dist)
    if spark.verify_resources():
        hookenv.status_set('maintenance', 'Installing Apache Spark')
        dist.add_dirs()
        dist.add_packages()
        spark.install()
        spark.setup_spark_config()
        spark.install_demo()
        set_state('spark.installed')


@when('spark.installed', 'hadoop.ready')
@when_not('spark.started')
def start_spark(hadoop):
    hookenv.status_set('maintenance', 'Setting up Apache Spark')
    spark = Spark(get_dist_config())

    spark.configure()
    spark.start()
    spark.open_ports()
    set_state('spark.started')
    hookenv.status_set('active', 'Ready')


@when('spark.started')
@when_not('hadoop.ready')
def stop_spark():
    hookenv.status_set('maintenance', 'Stopping Apache Spark')
    spark = Spark(get_dist_config())
    spark.close_ports()
    spark.stop()
    remove_state('spark.started')


@when('spark.started', 'client.related')
def client_present(client):
    client.set_installed()


@when('client.related')
@when_not('spark.started')
def client_should_stop(client):
    client.clear_installed()


@when('benchmark.related')
def register_benchmarks(benchmark):
    benchmarks = ['sparkpi']
    if hookenv.config('spark_bench_enabled'):
        benchmarks.extend(['logisticregression',
                           'matrixfactorization',
                           'pagerank',
                           'sql',
                           'streaming',
                           'svdplusplus',
                           'svm',
                           'trianglecount'])
    benchmark.register(benchmarks)
