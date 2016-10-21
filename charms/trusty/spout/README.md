Overview
--------

The Spout charm represents an Apache Storm spout.
Required Apache Storm version is 0.10 +.

Usage
-----

This charm can be used in the following way:

```
juju deploy cs:~tengu-bot/apache-zookeeper
juju deploy cs:~tengu-bot/storm storm-master
juju deploy cs:~tengu-bot/storm storm-worker
juju add-relation apache-zookeeper storm-master
juju add-relation apache-zookeeper storm-worker
juju add-relation storm-master:master storm-worker:worker

juju deploy cs:~tengu-bot/storm-topology
juju add-relation storm-topology storm-master
juju deploy cs:~tengu-bot/spout spout1
juju add-relation spout1 storm-master
juju add-relation spout1 storm-topology

juju set spout1 "class=https://raw.githubusercontent.com/xannz/WordCountExample/master/src/main/java/com/sborny/wordcountexample/RandomSentenceSpout.java"
```


# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

- Sander Borny <sander.borny@ugent.be>
- Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
