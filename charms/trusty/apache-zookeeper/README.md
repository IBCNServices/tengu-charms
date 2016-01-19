## Overview
Apache ZooKeeper is a high-performance coordination service for distributed
applications. It exposes common services such as naming, configuration
management, synchronization, and group services in a simple interface so you
don't have to write them from scratch. You can use it off-the-shelf to
implement consensus, group management, leader election, and presence protocols.


## Usage
Deploy a Zookeeper unit. With only one unit, the service will be running in
`standalone` mode:

    juju deploy apache-zookeeper zookeeper


## Scaling
Running ZooKeeper in `standalone` mode is convenient for evaluation, some
development, and testing. But in production, you should run ZooKeeper in
`replicated` mode. A replicated group of servers in the same application is
called a quorum, and in `replicated` mode, all servers in the quorum have
copies of the same configuration file.

Scaling Zookeeper to create a quorum is trivial. The following will add two
additional Zookeeper units and will automatically configure them with knowledge
of the other quorum members based on their peer relation to one another:

    juju add-unit -n 2 zookeeper


## Test the deployment
Test if the Zookeeper service is running by using the `zkServer.sh` script:

    juju run --service=zookeeper '/usr/lib/zookeeper/bin/zkServer.sh status'

A successful deployment will report the service mode as either `standalone`
(if only one Zookeeper unit has been deployed) or `leader` / `follower` (if
a Zookeeper quorum has been formed).


## Integrate Zookeeper into another charm
1) Add following lines to your charm's metadata.yaml:

    requires:
      zookeeper:
         interface: zookeeper

2) Add a `zookeeper-relation-changed` hook to your charm. Example contents:

    from charmhelpers.core.hookenv import relation_get
    ZK_hostname = relation_get('private-address')
    ZK_port = relation_get('port')


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
    juju resources fetch --all apache-zookeeper/resources.yaml -d /tmp/resources
    juju resources serve -d /tmp/resources

This will fetch all of the resources needed by this charm and serve them via a
simple HTTP server. You can then set the `resources_mirror` config option to
have the charm use this server for retrieving resources.


## Contact Information
[bigdata-dev@canonical.com](mailto:bigdata-dev@canonical.com)


## Help
- [Apache Zookeeper home page](https://zookeeper.apache.org/)
- [Apache Zookeeper issue tracker](https://issues.apache.org/jira/browse/ZOOKEEPER)
- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
