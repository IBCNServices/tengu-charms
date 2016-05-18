## Overview

Hue is an open-source Web interface that supports Apache Hadoop and its ecosystem

Hue aggregates the most common Apache Hadoop components into a single interface
and targets the user experience. Its main goal is to have the users "just use"
Hadoop without worrying about the underlying complexity or using a command line.

## Usage

This charm leverages our pluggable Hadoop model with the `hadoop-plugin`
interface. This means that you will need to deploy a base Apache Hadoop cluster
to run Hue. 
You may manually deploy the recommended environment as follows:

    juju deploy apache-hadoop-namenode namenode
    juju deploy apache-hadoop-resourcemanager resourcemanager
    juju deploy apache-hadoop-slave slave
    juju deploy apache-hadoop-plugin plugin
    juju deploy hue hue

    juju add-relation resourcemanager namenode
    juju add-relation slave resourcemanager
    juju add-relation slave namenode
    juju add-relation plugin resourcemanager
    juju add-relation plugin namenode
    juju add-relation plugin hue

At this point you will then need to expose hue:

    juju expose hue

And then browse to the HUE_IP:HUE_PORT shown in 'juju status --format tabular'

The reason for this is that the first login to hue via the web interface creates
the default admin user so we need to make sure you are the first person to 
log in.

The allowed Hadoop cluster operations should be available from the web interface.
By default HDFS file browsing and Hadoop job browsing should be available.
Additional features will be made available as you relate Hue to other charms,
as described below.


## Enabling Apache Hive features

Adding Apache Hive features to hive is as simple as deploying the Hive charm and
relating it to hive:


    juju deploy mysql
    juju set mysql binlog-format=ROW
    juju deploy apache-hive hive
    juju add-relation plugin hive

Now just add a relation between Hive and Hue

    juju add-relation hue hive

Hue should restart and in its updated interface you should be able to query Hive and browse
the metasotre.


## Enabling Apache Zookeeper features

Hue interacts with Zookeeper through the laters REST Api.
The steps for relating Hue to Zookeeper are as follows:

    juju deploy apache-zookeeper zookeeper
    juju set zookeeper rest=true

Now just add a relation between Zookeeper and Hue

    juju add-relation hue zookeeper

Hue should restart and in its updated interface you should be able to browse Zookeeper.


## Contact Information

- <bigdata-dev@lists.launchpad.net>


## Help

- [HUE home page](http://gethue.com)
- [HUE bug tracker](https://issues.cloudera.org/projects/HUE)
- `#juju` on `irc.freenode.net`
