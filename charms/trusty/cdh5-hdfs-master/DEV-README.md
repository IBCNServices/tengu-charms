## Overview

This charm provides storage resource management for an Apache Hadoop
deployment, and is intended to be used only as a part of that deployment.
This document describes how this charm connects to and interacts with the
other components of the deployment.


## Provided Relations

### namenode (interface: dfs)

This relation connects this charm to the charms which require a NameNode,
such as the apache-hadoop-yarn-master and apache-hadoop-plugin charms.
The relation exchanges the following keys:

* Sent to the plugin:

  * `private-address`: Address of this unit, to provide the NameNode
  * `has_slave`: Flag indicating if HDFS has at least one DataNode
  * `port`: Port where the NameNode is listening for HDFS operations (IPC)
  * `webhdfs-port`: Port for the NameNode web interface

* Received from the plugin:

  *There are no keys received from the plugin*

To use this interface, it is recommended that you use
[Charm Helpers](https://pypi.python.org/pypi/charmhelpers) and the relation
class provided in the
[Juju Big Data library](https://pypi.python.org/pypi/jujubigdata):

    from charmhelpers.core import unitdata
    from jujubigdata.relations import NameNode

    namenode = NameNode()
    if namenode.is_ready():
        namenode_units = unitdata.kv.get('relations.ready')['namenode']
        namenode_data = namenode_units.values()[0]
        print namenode_data['private-address']


## Required Relations

### datanode (interface: dfs-slave)

This relation connects this charm to the apache-hadoop-compute-slave charm.
It is a bi-directional interface, with the following keys being exchanged:

* Sent to compute-slave:

  * `private-address`: Address of this unit, to provide the NameNode
  * `has_slave`: Flag indicating if HDFS has at least one DataNode
  * `port`: Port where the NameNode is listening for HDFS operations (IPC)
  * `webhdfs-port`: Port for the NameNode web interface

* Received from compute-slave:

  * `private-address`: Address of the remote unit to be registered as a DataNode


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
