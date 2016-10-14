Overview
--------

The bolt charm represents an Apache Storm bolt.
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
juju deploy bolt splitsentencebolt
juju add-relation splitsentencebolt stormmaster
juju add-relation splitsentencebolt topo

juju set splitsentencebolt "class=https://raw.githubusercontent.com/xannz/WordCountExample/master/src/main/java/com/sborny/wordcountexample/SplitSentence.java"
```

To create a MongoDB bolt connect the bolt to a MongoDB charm. Set the database name or use the default test.
```
juju add-relation splitsentencebolt mongodb
juju set splitsentencebolt "database=demo"
```

Set the stream groupings with the `groupings` config option
```
juju set splitsentencebolt "groupings=otherbolt(FIELDS word)"
```

A bolt can be preconfigured by using the `prepare-methods` config option
```
juju set splitsentencebolt "prepare-methods=prepare(arg1);prepare2(arg1,arg2)"
```



# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

- Sander Borny <sander.borny@ugent.be>
- Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
