## Overview

The Apache Hadoop software library is a framework that allows for the
distributed processing of large data sets across clusters of computers
using a simple programming model.

This charm deploys a slave node running the NodeManager component
[Apache Hadoop 2.7.1](http://hadoop.apache.org/docs/r2.7.1/),
which provides computation resources to the platform.

## Usage

This charm is intended to be deployed via one of the
[apache bundles](https://jujucharms.com/u/bigdata-charmers/#bundles).
For example:

    juju quickstart apache-analytics-sql

This will deploy the Apache Hadoop platform with Apache Hive available to
perform SQL-like queries against your data.

You can also manually load and run map-reduce jobs via the plugin charm
included in the bigdata bundles linked above:

    juju scp my-job.jar plugin/0:
    juju ssh plugin/0
    hadoop jar my-job.jar


### Scaling

The nodemanager node is the "workhorse" of the Apache Hadoop platform.
To scale your deployment's performance, you can simply add more nodemanager 
units.  For example, to add three mode units:

    juju add-unit compute-slave -n 3


## Monitoring

This charm supports monitoring via Ganglia.  To enable monitoring, you must
do **both** of the following (the order does not matter):

 * Add a relation to the [Ganglia charm][] via the `:master` relation
 * Enable the `ganglia_metrics` config option

You must **also** enable metrics on [yarn-master][] and / or [hdfs-master][]
to initiate the restart of the NodeManager and / or DataNode components for
them to begin collecting metrics.

For example:

    juju add-relation nodemnager ganglia:master
    juju add-relation yarn-master ganglia:master
    juju set nodemanager ganglia_metrics=true
    juju set yarn-master ganglia_metrics=true


## Deploying in Network-Restricted Environments

The Apache Hadoop charms can be deployed in environments with limited network
access. To deploy in this environment, you will need a local mirror to serve
the packages and resources required by these charms.


### Mirroring Packages

You can setup a local mirror for apt packages using squid-deb-proxy.
For instructions on configuring juju to use this, see the
[Juju Proxy Documentation](https://juju.ubuntu.com/docs/howto-proxies.html).


### Mirroring Resources

In addition to apt packages, the Apache Hadoop charms require a few binary
resources, which are normally hosted on Launchpad. If access to Launchpad
is not available, the `jujuresources` library makes it easy to create a mirror
of these resources:

    sudo pip install jujuresources
    juju-resources fetch --all /path/to/resources.yaml -d /tmp/resources
    juju-resources serve -d /tmp/resources

This will fetch all of the resources needed by this charm and serve them via a
simple HTTP server. The output from `juju-resources serve` will give you a
URL that you can set as the `resources_mirror` config option for this charm.
Setting this option will cause all resources required by this charm to be
downloaded from the configured URL.

You can fetch the resources for all of the Apache Hadoop charms
(`apache-hadoop-hdfs-master`, `apache-hadoop-yarn-master`,
`apache-hadoop-hdfs-secondary`, `apache-hadoop-plugin`, etc) into a single
directory and serve them all with a single `juju-resources serve` instance.


## Contact Information

- <bigdata@lists.ubuntu.com>


## Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)


[Ganglia charm]: http://jujucharms.com/ganglia/
[yarn-master]: http://jujucharms.com/apache-hadoop-yarn-master/
[hdfs-master]: http://jujucharms.com/apache-hadoop-hdfs-master/
