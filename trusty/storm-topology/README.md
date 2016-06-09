Overview
--------

The storm-topology charm represents an Apache Storm topology. 
 
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

juju set topo "name=WordCountTopology"
juju set topo "dependencies=https://raw.githubusercontent.com/xannz/WordCountExample/master/dependencies"
```



