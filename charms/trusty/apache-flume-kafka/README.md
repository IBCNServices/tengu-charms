## Overview

Flume is a distributed, reliable, and available service for efficiently
collecting, aggregating, and moving large amounts of log data. It has a simple
and flexible architecture based on streaming data flows. It is robust and fault
tolerant with tunable reliability mechanisms and many failover and recovery
mechanisms. It uses a simple extensible data model that allows for online
analytic application. Learn more at [flume.apache.org](http://flume.apache.org).

This charm provides a Flume agent designed to ingest messages published to
a Kafka topic and send them to the `apache-flume-hdfs` agent for storage in
the shared filesystem (HDFS) of a connected Hadoop cluster. This leverages the
KafkaSource jar packaged with Flume. Learn more about the
[Flume Kafka Source](https://flume.apache.org/FlumeUserGuide.html#kafka-source).


## Usage

This charm leverages our pluggable Hadoop model with the `hadoop-plugin`
interface. This means that you will need to deploy a base Apache Hadoop cluster
extended with Flume and Kafka. The suggested deployment method is to use the
[apache-ingestion-flume-kafka](https://jujucharms.com/u/bigdata-dev/apache-ingestion-flume-kafka/)
bundle. This will deploy the Apache Hadoop platform with Apache Flume
and Apache Kafka communicating with the cluster by relating to the
`apache-hadoop-plugin` subordinate charm:

    juju quickstart u/bigdata-dev/apache-ingestion-flume-kafka

Alternatively, you may manually deploy the recommended environment as follows:

    juju deploy apache-hadoop-hdfs-master hdfs-master
    juju deploy apache-hadoop-yarn-master yarn-master
    juju deploy apache-hadoop-compute-slave compute-slave
    juju deploy apache-hadoop-plugin plugin
    juju deploy apache-flume-hdfs flume-hdfs
    juju deploy apache-flume-kafka flume-kafka
    juju deploy apache-kafka kafka
    juju deploy apache-zookeeper zookeeper

    juju add-relation yarn-master hdfs-master
    juju add-relation compute-slave yarn-master
    juju add-relation compute-slave hdfs-master
    juju add-relation plugin yarn-master
    juju add-relation plugin hdfs-master
    juju add-relation flume-hdfs plugin
    juju add-relation flume-kafka flume-hdfs
    juju add-relation flume-kafka kafka
    juju add-relation kafka zookeeper

## Configure the environment

The default Kafka topic where messages are published is unset. Set this to
an existing Kafka topic as follows:

    juju set flume-kafka kafka_topic='<topic_name>'

If you don't have a Kafka topic, you may create one (and verify successful
creation) with:

    juju action do kafka/0 create-topic topic=<topic_name> \
     partitions=1 replication=1
    juju action fetch <id>  # <-- id from above command

You'll also need to specify the Zookeeper connection string for this charm. In
the future, this value will be automatically available via the Kafka relation.
Retrieve the current Zookeeper connection string with:

    juju action do kafka/0 list-zks
    juju action fetch <id>  # <-- id from above command

Set the <ip>:<port> information from the above `zookeepers` output in this
charm:

    juju set flume-kafka zookeeper_connect='<ip:port>'

Once the Flume agents start, messages will start flowing into
HDFS in year-month-day directories here: `/user/flume/flume-kafka/%y-%m-%d`.


## Test the deployment

Generate Kafka messages on the `flume-kafka` unit with the producer script:

    juju ssh flume-kafka/0
    kafka-console-producer.sh --broker-list localhost:9092 --topic <topic_name>
    <type message, press Enter>

To verify these messages are being stored into HDFS, SSH to the `flume-hdfs`
unit, locate an event, and cat it:

    juju ssh flume-hdfs/0
    hdfs dfs -ls /user/flume/flume-kafka  # <-- find a date
    hdfs dfs -ls /user/flume/flume-kafka/yyyy-mm-dd  # <-- find an event
    hdfs dfs -cat /user/flume/flume-kafka/yyyy-mm-dd/FlumeData.[id]


## Contact Information

- <bigdata@lists.ubuntu.com>


## Help

- [Apache Flume home page](http://flume.apache.org/)
- [Apache Flume bug tracker](https://issues.apache.org/jira/browse/flume)
- [Apache Flume mailing lists](https://flume.apache.org/mailinglists.html)
- `#juju` on `irc.freenode.net`
