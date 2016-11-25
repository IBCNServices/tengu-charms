# Overview
<p>
Apache NiFi is an easy, powerful, and reliable system to process and distribute data. More info can be found
<a href="https://nifi.apache.org/developer-guide.html">here.</a>
</p>

# Usage
This charm uses JuJu 2 to access the Apache Nifi tarball.
Apache NiFi depends on Java 8. This is automatically installed if necessary.
To run Apache NiFi in standalone mode:
```
juju deploy apache-nifi
```
The `--resource` flag can be used to upload the tarball from your local disk:
```
juju deploy apache-nifi --resource apache-nifi=/PATH/to/file
```
When you want to run Apache NiFi in a cluster, a relation with Apache Zookeeper must be made:
```
juju add-relation apache-nifi zookeeper
```
<p>
When Apache NiFi is running in a cluster, it will detect changes in the Apache Zookeeper setup and react to them if
necessary. Apache NiFi can be changed to run in a standalone configuration when it's running in a cluster by removing the
relation with Apache Zookeeper:
</p>
```
juju remove-relation apache-nifi zookeeper
```
<p>
<strong>Beware! When the relation is removed, Apache NiFi does not start automatically!</strong> This is to prevent problems with multiple
instances of Apache NiFi to run on the same dataset. Manual intervention is required to remove the obsolete nodes and to
change the dataflow of the other nodes.
</p>
<p>
After deploy or add-relation, the user interface of Apache NiFi is accessible through your browser at `<ip-address>:<nifi-port>`. The port defaults to 8080. However, it can take up to 2 minutes after install before the user interface is accessible, or all the nodes in the cluster are visible in the user interface.
</p>
# Configuration options
The following configuration options are available:
* `nifi-port`
Defaults to 8080. The user interface is accessible on this port.
* `cluster-port`
Defaults to 8517. The nodes communicate to the Cluster Coordinator on this port.
* `java-major`
Defaults to 8. <strong>This may not be set to a lower version!</strong>

<p>
All other configuration options have to be set manually in the Apache NiFi configuration files. More info can be found
<a href="https://nifi.apache.org/docs/nifi-docs/html/administration-guide.html">here.</a>
</p>
# Bugs
Report bugs on <a href="https://github.com/IBCNServices/tengu-charms/issues">Github</a>
# Author
Mathijs Moerman <a href="mailto:mathijs.moerman@qrama.io">mathijs.moerman@qrama.io</a>
