## Overview

This charm provides computation and storage resources for an Apache Hadoop
deployment, and is intended to be used only as a part of that deployment.
This document describes how this charm connects to and interacts with the
other components of the deployment.


## Provided Relations

### resourcemanager (interface: mapred)

This relation connects this charm to the apache-hadoop-plugin charm.
The relation exchanges the following keys:

* Sent to the plugin:

  * `private-address`: Address of this unit, to provide the ResourceManager
  * `has_slave`: Flag indicating if YARN has at least one NodeManager
  * `port`: Port where the ResourceManager is listening for YARN operations (IPC)
  * `historyserver-port`: JobHistory port (IPC)

* Received from the plugin:

  *There are no keys received from the plugin*

To use this interface, it is recommended that you use
[Charm Helpers](https://pypi.python.org/pypi/charmhelpers) and the relation
class provided in the
[Juju Big Data library](https://pypi.python.org/pypi/jujubigdata):

    from charmhelpers.core import unitdata
    from jujubigdata.relations import ResourceManager

    resourcemanager = ResourceManager()
    if resourcemanager.is_ready():
        rm_units = unitdata.kv.get('relations.ready')['resourcemanager']
        rm_data = rm_units.values()[0]
        print rm_data['private-address']


## Required Relations

### namenode (interface: dfs)

This relation connects this charm to the apache-hadoop-hdfs-master charm.
The relation exchanges the following keys:

* Sent to hdfs-master:

  *There are no keys sent to hdfs-master*

* Received from hdfs-master:

  * `private-address`: Address of the HDFS master unit, to provide the NameNode
  * `has_slave`: Flag indicating if HDFS has at least one DataNode
  * `port`: Port where the NameNode is listening for HDFS operations (IPC)
  * `webhdfs-port`: Port for the NameNode web interface


### nodemanager (interface: mapred-slave)

This relation connects this charm to the apache-hadoop-compute-slave charm.
The relation exchanges the following keys:

* Sent to compute-slave:

  * `private-address`: Address of the YARN master unit, to provide the ResourceManager
  * `has_slave`: Flag indicating if YARN has at least one NodeManager
  * `port`: Port where the ResourceManager is listening for YARN operations (IPC)
  * `historyserver-port`: JobHistory port (IPC)

* Received from compute-slave:

  * `private-address`: Address of the remote unit, to be registered as a NodeManager


## Manual Deployment

The easiest way to deploy an Apache Hadoop platform is to use one of
the [apache bundles](https://jujucharms.com/u/bigdata-charmers/#bundles).
However, to manually deploy the base Apache Hadoop platform without using one
of the bundles, you can use the following:

    juju deploy apache-hadoop-hdfs-master hdfs-master
    juju deploy apache-hadoop-hdfs-secondary secondary-namenode
    juju deploy apache-hadoop-yarn-master yarn-master
    juju deploy apache-hadoop-compute-slave compute-slave -n3
    juju deploy apache-hadoop-plugin plugin

    juju add-relation yarn-master hdfs-master
    juju add-relation secondary-namenode hdfs-master
    juju add-relation compute-slave yarn-master
    juju add-relation compute-slave hdfs-master
    juju add-relation plugin yarn-master
    juju add-relation plugin hdfs-master

This will create a scalable deployment with separate nodes for each master,
and a three unit compute slave (NodeManager and DataNode) cluster.  The master
charms also support co-locating using the `--to` option to `juju deploy` for
more dense deployments.
