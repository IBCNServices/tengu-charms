#!/usr/bin/python3 pylint:disable=c0111,e0401
from charmhelpers.core import hookenv
from jujubigdata.utils import DistConfig
from charms import layer # pylint: disable=e0611
from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state
from charms.reactive.helpers import data_changed
from charms.spark import Spark
from charms.livy import Livy


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
def report_waiting(hadoop):# pylint: disable=w0613
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')


# TODO: support standalone mode when Yarn not connected
@when('hadoop.ready')
@when_not('spark.installed')
def install_spark(hadoop):# pylint: disable=w0613
    dist = DistConfig(data=layer.options('apache-spark'))
    spark = Spark(dist)
    if spark.verify_resources():
        hookenv.status_set('maintenance', 'Installing Apache Spark')
        spark.install()
        spark.setup_spark_config()
        spark.install_demo()
        set_state('spark.installed')


@when('hadoop.ready', 'spark.installed')
@when_not('livy.installed')
def install_livy(hadoop):# pylint: disable=w0613
    dist = DistConfig(data=layer.options('livy'))
    livy = Livy(dist)
    if livy.verify_resources():
        hookenv.status_set('maintenance', 'Installing Livy REST server')
        livy.install()
        set_state('livy.installed')


@when('spark.installed', 'livy.installed', 'hadoop.ready')
@when_not('spark.started')
def start_spark(hadoop):# pylint: disable=w0613
    hookenv.status_set('maintenance', 'Setting up Apache Spark')
    dist = DistConfig(data=layer.options('apache-spark'))
    spark = Spark(dist)
    spark.configure()
    spark.start()
    spark.open_ports()
    set_state('spark.started')


@when('spark.installed', 'livy.installed', 'hadoop.ready', 'spark.started')
@when_not('livy.started')
def start_livy(hadoop):# pylint: disable=w0613
    hookenv.status_set('maintenance', 'Setting up Livy REST server')
    dist = DistConfig(data=layer.options('livy'))
    livy = Livy(dist)
    mode = hookenv.config()['spark_execution_mode']
    livy.configure(mode)
    livy.start()
    livy.open_ports()
    set_state('livy.started')
    hookenv.status_set('active', 'Ready')


@when('spark.installed', 'livy.installed', 'hadoop.ready', 'spark.started', 'livy.started')
def reconfigure_spark(hadoop):# pylint: disable=w0613
    config = hookenv.config()
    if not data_changed('configuration', config):
        return

    hookenv.status_set('maintenance', 'Configuring Apache Spark and Livy REST server')
    dist = DistConfig(data=layer.options('apache-spark'))
    spark = Spark(dist)
    dist = DistConfig(data=layer.options('livy'))
    livy = Livy(dist)

    livy.stop()
    spark.stop()
    spark.configure()
    mode = hookenv.config()['spark_execution_mode']
    livy.configure(mode)
    spark.start()
    livy.start()
    hookenv.status_set('active', 'Ready')


@when('spark.started', 'livy.started')
@when_not('hadoop.ready')
def stop_spark():
    hookenv.status_set('maintenance', 'Stopping Livy REST server')
    dist = DistConfig(data=layer.options('livy'))
    livy = Livy(dist)
    livy.close_ports()
    livy.stop()
    remove_state('livy.started')

    hookenv.status_set('maintenance', 'Stopping Apache Spark')
    dist = DistConfig(data=layer.options('apache-spark'))
    spark = Spark(dist)
    spark.close_ports()
    spark.stop()
    remove_state('spark.started')


@when('spark.started', 'livy.started', 'client.joined')
def client_present(client):
    dist = DistConfig(data=layer.options('livy'))
    rest_port = dist.port('livy')
    client.send_rest_port(rest_port)
    client.set_spark_started()


@when('client.joined')
@when_not('spark.started')
def client_should_stop(client):
    client.clear_spark_started()


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
