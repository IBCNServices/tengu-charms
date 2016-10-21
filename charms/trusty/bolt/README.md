Overview
--------

The bolt charm represents an Apache Storm bolt.
Required Apache Storm version is 0.10 +.

Usage
-----

## Custom Bolt

This bolt can run your own class in the following way:

```bash
juju deploy zookeeper
juju deploy cs:~tengu-bot/storm nimbus
juju deploy cs:~tengu-bot/storm worker
juju add-relation zookeeper nimbus
juju add-relation zookeeper worker
juju add-relation nimbus:master worker:worker

juju deploy cs:~tengu-bot/storm-topology
juju add-relation storm-topology nimbus
juju deploy cs:~tengu-bot/bolt splitsentencebolt
juju add-relation splitsentencebolt nimbus
juju add-relation splitsentencebolt storm-topology

juju set splitsentencebolt "class=https://raw.githubusercontent.com/xannz/WordCountExample/master/src/main/java/com/sborny/wordcountexample/SplitSentence.java"
```

Set the stream groupings with the `groupings` config option

```bash
juju set splitsentencebolt "groupings=otherbolt(FIELDS word)"
```

A bolt can be preconfigured by using the `prepare-methods` config option

```bash
juju set splitsentencebolt "prepare-methods=prepare(arg1);prepare2(arg1,arg2)"
```


## MongoDB bolt

This class can also be configured to send the data it receives to MongoDB. This is done using the following commands.

*Note that the bolt **has to be connected to both `nimbus` and `storm-topology` before adding the relation to MongoDB.***

```bash
juju deploy cs:~tengu-bot/bolt mongobolt
juju add-relation mongobolt nimbus
juju add-relation mongobolt storm-topology
juju add-relation mongobolt mongodb
juju set mongobolt database=demo
```


# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

- Sander Borny <sander.borny@ugent.be>
- Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
