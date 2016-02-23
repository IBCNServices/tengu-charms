# Overview

This interface layer handles the communication between the [ResourceManager][] and
[NodeManager][] component of the Apache Hadoop cluster charms.


# Usage

## Requires

The ResourceManager requires this interface, to gain access to one or more NodeManager
units.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.related` One or more NodeManagers have connected.  The
    charm should call the following methods to provide the appropriate
    information to the NodeManagers:
      * `send_spec(spec)`
      * `send_host(host)`
      * `send_ports(port, port, hs_http, hs_ipc)`
      * `send_ssh_key(ssh_key)`
      * `send_hosts_map(hosts_map)`

  * `{relation_name}.registered` One or more NodeManagers are ready to use.
    Information about the registered NodeManagers can be gotten from the method:
      * `nodemanagers()`

  * `{relation_name}.departing` One or more NodeManagers are about to depart,
    and the ResourceManager should remove them from the pool of slaves.
    Information about the departing NodeManagers can be gotten from the method:
      * `nodemanagers()`


## Provides

This interface layer will set the following states, as appropriate:

  * `{relation_name}.related` The relation is established, but YARN may not yet
    have provided any connection or service information.

  * `{relation_name}.ready` The ResourceManager has provided all of the necessary
    information, and this unit is present in the hosts map, indicating that
    it can be seen by the ResourceManager and all other NodeManagers.
    The provided information can be accessed via the following methods:
      * `spec()`
      * `host()`
      * `port()`
      * `hs_http()`
      * `hs_ipc()`
      * `ssh_key()`
      * `hosts_map()`

    The NodeManager should now register itself with the following method:
      * `register()`


# Contact Information

- <bigdata@lists.ubuntu.com>


# Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)


[ResourceManager]: https://github.com/juju-solutions/layer-apache-hadoop-resourcemanager/
[NodeManager]: https://github.com/juju-solutions/layer-apache-hadoop-nodemanager/
