# Overview

This interface layer handles the communication between a Hadoop client and a
Hadoop cluster via the `hadoop-plugin` interface protocol.

# Usage

## Provides

This is the side that clients will use to connect to Hadoop.  The client acts
as the principal, or host container, to the plugin, and thus must provide a
`scope: container` relation for the plugin to connect to.

The interface layer will set the following states for the client to react to,
as appropriate:

  * `{relation_name}.connected` The relation between the client and the plugin
     is established, but one or both of Yarn or HDFS may not yet be available
     to provide their service.

  * `{relation_name}.yarn.ready` Yarn is connected and ready to run map-reduce jobs.

  * `{relation_name}.hdfs.ready` HDFS is connected and ready to store data

  * `{relation_name}.ready` **Both** Yarn and HDFS are connected and ready.

In addition to setting the above states, the charm providing this relation (e.g.,
[apache-hadoop-plugin][]) will install a JRE and the Hadoop API Java libraries,
will manage the Hadoop configuration in `/etc/hadoop/conf`, and will configure
the environment in `/etc/environment`.  The endpoint will also ensure that the
distribution, version, Java, etc. are all compatible to ensure a properly
functioning Hadoop ecosystem.

An example of a charm using this interface would be:

```python
@hook('install')
def install():
    spark.install()

@when_not('hadoop.connected')
def blocked():
    hookenv.status_set('blocked', 'Please add relation to Hadoop Plugin')

@when('hadoop.connected')
@when_not('hadoop.ready')
def waiting(hadoop):
    hookenv.status_set('waiting', 'Waiting for Hadoop to become ready')

@when('hadoop.ready')
def hadoop_ready(hadoop):
    spark.configure()
    spark.start()
    status_set('active', 'Spark is ready')
```


## Requires

This is the side that a Hadoop Plugin charm (e.g., [apache-hadoop-plugin][])
will use to present a unified connection to a Hadoop cluster.  The plugin acts
as the subordinate to the principal client charm, deploying directly within the
principal's existing container, and thus requires a `scope: container` relation
to connect to.

The interface layer will set the following state for the plugin to react to, as
appropriate:

  * `{relation_name}.connected` The relation between the plugin and the client
     is established, and the plugin should install all libraries and dependencies,
     configure the environment, etc.  The plugin should also call the methods on
     the instance provided by this state to indicate when Yarn and HDFS are ready.

The instance passed into the handler for the above state supports the following
methods:

  * `set_yarn_ready(hosts, port, hs_http, hs_ipc)`
    Let the client know that Yarn is ready to run map-reduce jobs.

  * `set_hdfs_ready(hosts, port)`
    Let the client know that HDFS is ready to store data.

An example of a charm using this interface would be:

```python
@when('client.connected')
def install(client):
    hadoop.install()
    hadoop.configure_client()

@when('client.connected', 'yarn.ready')
def yarn_ready(client, yarn):
    hadoop.configure_yarn_client(yarn)
    client.set_yarn_ready(
        yarn.resourcemanagers(), yarn.port(),
        yarn.hs_http(), yarn.hs_ipc())

@when('client.connected', 'hdfs.ready')
def hdfs_ready(client, hdfs):
    hadoop.configure_hdfs_client(hdfs)
    client.set_hdfs_ready(hdfs.namenodes(), hdfs.port())
```


# Contact Information

- <bigdata@lists.ubuntu.com>


# Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)


[apache-hadoop-plugin]: https://jujucharms.com/apache-hadoop-plugin/
