# Overview

This interface layer handles the communication with a Hadoop deployment via the
`hadoop-interface` interface protocol.  It will set two states when appropriate:

  * `{relation_name}.yarn.ready` indicates that Yarn is available and ready to accept jobs
  * `{relation_name}.hdfs.ready` indicates that HDFS is available and ready to store data

In addition, the charm providing this relation (e.g., [apache-hadoop-plugin][])
will install a JRE and the Hadoop API Java libraries, will manage the Hadoops
configuration in `/etc/hadoop/conf`, and will configure the environment in
`/etc/environment`.  The endpoint will also ensure that the distribution,
version, Java, etc. are all compatible to ensure a properly functioning
Hadoop ecosystem.


# Example Usage

An example of a charm using this interface would be:

```python
@hook('install')
def install():
    spark.install()

@when('hadoop.yarn.ready', 'hadoop.hdfs.ready')
def hadoop_ready(yarn, hdfs):
    spark.configure()
    spark.start()
    status_set('active', 'Spark is ready')
```


# Contact Information

- <bigdata@lists.ubuntu.com>


# Hadoop

- [Apache Hadoop](http://hadoop.apache.org/) home page
- [Apache Hadoop bug trackers](http://hadoop.apache.org/issue_tracking.html)
- [Apache Hadoop mailing lists](http://hadoop.apache.org/mailing_lists.html)
- [Apache Hadoop Juju Charm](http://jujucharms.com/?text=hadoop)


[apache-hadoop-plugin]: https://jujucharms.com/apache-hadoop-plugin/
