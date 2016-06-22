# Overview

This charm provides access to Storm, the distributed realtime computation system. The Charm allows you
to setup a master and one or more workers. The supervisor contains Nimbus and the UI.
The workers contain a supervisor, a DRPC server and one or more workers when a topology is deployed.
A relation with zookeeper is required.

# Usage

To setup a test environment:

    juju bootstrap
    juju deploy zookeeper
    juju deploy local:storm storm-master
    juju deploy local:storm storm-worker
    juju add-relation storm-master zookeeper
    juju add-relation storm-worker zookeeper
    juju add-relation storm-master:master storm-worker:worker
    juju expose storm-master
    juju expose storm-worker

The UI is running on port 8080 of the stormmaster.

Optionally you can use a configuration file, e.g. config.yaml.

An example could be:

    stormworker:
      nimbusmemory: 512
      uimemory: 384
      supervisormemory: 128
      workermemory: 128
      nimbusport: 6627
      uiport: 8080
      zookeeperport: 2181
      drpcport: 3772
      numberofworkers: 5
      startingworkerport: 6700

The memory requirements of several components can be specified in
megabytes: nimbus, ui, supervisor and worker.

Finally each worker node can have multiple workers running on it.
The startingworkerport defines the port of the first worker, e.g. 6700.
The numberofworkers defines how many workers are started up on each worker
node. The ports will be a combination of these two configuration options.
If the starting port is 6700 and the number of workers is 3, then the ports
that are used will be: 6700 6701 6702.

You can use `add-unit` to add additional workers. However for the moment the
master can not be scaled to more than one. In order for the master to be scaled,
a distributed file system would have to synchronize /mnt/storm between different
peers and if the master died, a zookeeper master selection process would have to
select a new master and all workers would have to change their nimbus server
reference to point to the new master and restart.

# Commands (execute on nimbus)

Deploy storm topology

    /opt/storm/latest/bin/storm jar <path.to.Main> <args>

Kill storm topology

    /opt/storm/apache-storm-0.9.3/bin/storm kill <topology-name>

Storm logs:

    /opt/storm/latest/logs

# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
 - Maarten Ectors <maarten.ectors@canonical.com>
