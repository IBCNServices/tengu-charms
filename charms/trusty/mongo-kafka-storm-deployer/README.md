Overview
========

The mongo-kafka-storm-deployer provides a method to deploy a storm topology whenever it detect relations to MongoDB, Zookeeper and Kafka. When a relation breaks the topology will be undeployed.

Usage
=====

The storm topology to deploy has to be located in /tmp on the machine wich hosts the stormmaster.
An example of an environment:
```
juju deploy zookeeper
juju deploy storm stormmaster
juju deploy storm stormworker
juju deploy mongo-kafka-storm-deployer deployer
juju deploy mongodb
juju deploy apache-kafka kafka

juju action do kafka/0 create-topic topic=test partitions=1 replication=1
juju action fetch <id>

juju add-relation zookeeper stormmaster
juju add-relation zookeeper stormworker
juju add-relation zookeeper kafka
juju add-relation stormmaster:master stormworker:worker
juju add-relation deployer stormmaster
juju add-relation deployer mongodb
juju add-relation deployer zookeeper
juju add-relation deployer kafka

```

Known Issues
============
Currently only one topology will be deployed.
Storm does not support multiple versions of the same topology with the same name so assure that each time the name of the topology is different. You can use a version number for instance. The deployer will not deploy the topology if it is already deployed.



# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

- Sander Borny <sander.borny@ugent.be>
- Maarten Ectors <maarten.ectors@canonical.com>
- Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
- Rocket icon made by [Dave Gandy](http://www.flaticon.com/authors/dave-gandy) from [www.flaticon.com](http://www.flaticon.com) licensed as [Creative Commons BY 3.0](http://creativecommons.org/licenses/by/3.0/)
