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
