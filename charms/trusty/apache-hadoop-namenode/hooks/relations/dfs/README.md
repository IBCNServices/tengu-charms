# Overview

This interface layer handles the communication with HDFS via the `dfs` interface
protocol.  It is intended for internal use within the Hadoop cluster charms.
For typical usage, [interface-hadoop-plugin][] should be used instead.


# Usage

## Requires

Charms requiring this interface can be clients, DataNodes, or SecondaryNameNodes.
Clients simply depend on HDFS to serve as a distributed file system to them, while
DataNodes and SecondaryNameNodes register to provide additional services back.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The relation is established, but HDFS may not yet
    have provided any connection or service information.

  * `{relation_name}.ready` HDFS has provided its connection and service
    information, and is ready to serve as a distributed file system.
    The provided information can be accessed via the following methods:
      * `hosts_map()`
      * `port()`
      * `webhdfs_port()`

For example, a typical client would respond to `{relation_name}.ready`:

```python
@when('flume.installed', 'hdfs.ready')
def hdfs_ready(hdfs):
    flume.configure(hdfs)
    flume.start()
```


## Provides

A charm providing this interface is providing the HDFS service.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.clients` One or more clients of any type have
    been related.  The charm should call the following methods to provide the
    appropriate information to the clients:
      * `send_spec(spec)`
      * `send_hosts_map(hosts)`
      * `send_ports(port, webhdfs_port)`
      * `send_ready(ready)`

Example:

```python
@when('namenode.clients')
@when('hdfs.ready')
def serve_client(client):
    client.send_spec(utils.build_spec())
    client.send_ports(dist_config.get('port'), dist_config.get('webhdfs_port'))
    client.send_ready(True)

@when('namenode.clients')
@when_not('hdfs.ready')
def check_ready(client):
    client.send_ready(False)
```


# Contact Information

- <bigdata@lists.ubuntu.com>


# Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)
