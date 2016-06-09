Overview
--------

The Kafka-Spout charm represents an Apache Storm Kafka spout. 
 
Usage
-----

This charm can be used in the following way:

```
juju deploy zookeeper
juju deploy storm stormmaster
juju deploy storm stormworker
juju add-relation zookeeper stormmaster
juju add-relation zookeeper stormworker
juju add-relation stormmaster:master stormworker:worker

juju deploy storm-topology topo
juju add-relation topo stormmaster
juju deploy kafka-spout kspout
juju add-relation kspout stormmaster
juju add-relation kspout topo

juju set kspout "config=https://raw.githubusercontent.com/xannz/WordCountExample/master/kafkaconfig.yaml"
juju set kspout "spoutconfigname=spoutConfig"
```

The `spoutconfigname` must match the id in the config file.

