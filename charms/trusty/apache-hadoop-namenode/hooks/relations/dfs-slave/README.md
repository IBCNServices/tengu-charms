# Overview

This interface layer handles the communication between the [NameNode][] and
[DataNode][] component of the Apache Hadoop cluster charms.


# Usage

## Requires

The NameNode requires this interface, to gain access to one or more DataNode
units.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` One or more DataNodes have connected.  The
    charm should call the following methods to provide the appropriate
    information to the DataNodes:
      * `send_spec(spec)`
      * `send_host(host)`
      * `send_ports(port, webhdfs_port)`
      * `send_ssh_key(ssh_key)`
      * `send_hosts_map(hosts_map)`

  * `{relation_name}.departing` One or more DataNodes are about to depart,
    and the NameNode should remove them from the pool of slaves.
    Information about the departing DataNodes can be gotten from the method:
      * `datanodes()`


## Provides

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The relation is established, but HDFS may not yet
    have provided any connection or service information.

  * `{relation_name}.ready` The NameNode has provided all of the necessary
    information, and this unit is present in the hosts map, indicating that
    it can be seen by the NameNode and all other DataNodes.
    The provided information can be accessed via the following methods:
      * `spec()`
      * `host()`
      * `port()`
      * `webhdfs_port()`
      * `ssh_key()`
      * `hosts_map()`


# Contact Information

- <bigdata@lists.ubuntu.com>


# Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)


[NameNode]: https://github.com/juju-solutions/layer-apache-hadoop-namenode/
[DataNode]: https://github.com/juju-solutions/layer-apache-hadoop-datanode/
