Overview
--------

The Spout charm represents an Apache Storm spout. 
Required Apache Storm version is 0.10 +.
 
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
juju deploy spout spout1
juju add-relation spout1 stormmaster
juju add-relation spout1 topo

juju set spout1 "class=https://raw.githubusercontent.com/xannz/WordCountExample/master/src/main/java/com/sborny/wordcountexample/RandomSentenceSpout.java"
```

