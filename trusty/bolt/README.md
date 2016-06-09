Overview
--------

The bolt charm represents an Apache Storm bolt. 
 
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



