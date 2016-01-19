## Overview
Apache Kafka is an open-source message broker project developed by the Apache
Software Foundation written in Scala. The project aims to provide a unified,
high-throughput, low-latency platform for handling real-time data feeds. Learn
more at [kafka.apache.org](http://kafka.apache.org/).


## Usage
Kafka requires the Zookeeper distributed coordination service. Deploy and
relate them as follows:

    juju deploy apache-zookeeper zookeeper
    juju deploy apache-kafka kafka
    juju add-relation kafka zookeeper

Once deployed, we can list the zookeeper servers that our kafka brokers
are connected to. The following will list `<ip>:<port>` information for each
zookeeper unit in the environment (e.g.: `10.0.3.221:2181`).

    juju action do kafka/0 list-zks
    juju action fetch <id>  # <-- id from above command

We can create a Kafka topic with:

    juju action do kafka/0 create-topic topic=<topic_name> \
     partitions=<#> replication=<#>
    juju action fetch <id>  # <-- id from above command

We can list topics with:

    juju action do kafka/0 list-topics
    juju action fetch <id>  # <-- id from above command

We can write to a topic with:

    juju action do kafka/0 write-topic topic=<topic_name> data=<data>
    juju action fetch <id>  # <-- id from above command

We can read from a topic with:

    juju action do kafka/0 read-topic topic=<topic_name> partition=<#>
    juju action fetch <id>  # <-- id from above command

And finally, we can delete a topic with:

    juju action do kafka/0 delete-topic topic=<topic_name>
    juju action fetch <id>  # <-- id from above command

## Deploying in Network-Restricted Environments
This charm can be deployed in environments with limited network access. To
deploy in this environment, you will need a local mirror to serve the packages
and resources required by this charm.

### Mirroring Packages
You can setup a local mirror for apt packages using squid-deb-proxy.
For instructions on configuring juju to use this, see the
[Juju Proxy Documentation](https://juju.ubuntu.com/docs/howto-proxies.html).

### Mirroring Resources
In addition to apt packages, this charm requires a few binary resources
which are normally hosted on Launchpad. If access to Launchpad is not
available, the `jujuresources` library makes it easy to create a mirror
of these resources:

    sudo pip install jujuresources
    juju-resources fetch --all /path/to/resources.yaml -d /tmp/resources
    juju-resources serve -d /tmp/resources

This will fetch all of the resources needed by this charm and serve them via a
simple HTTP server. The output from `juju-resources serve` will give you a
URL that you can set as the `resources_mirror` config option for this charm.
Setting this option will cause all resources required by this charm to be
downloaded from the configured URL.


## Contact Information
- <bigdata-dev@lists.launchpad.net>


## Help
- [Apache Kafka home page](http://kafka.apache.org/)
- [Apache Kafka issue tracker](https://issues.apache.org/jira/browse/KAFKA)
- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
