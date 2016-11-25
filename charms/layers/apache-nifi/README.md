# Overview
<p>
Apache NiFi is an easy, powerful, and reliable system to process and distribute data. More info can be found
<a href="https://nifi.apache.org/developer-guide.html">here.</a>
</p>

# Usage
This charm uses JuJu 2 to add the Apache Nifi tarbal.
Apache NiFi depends on Java 8. This is automatically installed if necessary.
To use the Apache NiFi charm:
```
juju deploy apache-nifi
```
The `--resource` flag can be used to upload the install tarbal from your local disk:
```
juju deploy apache-nifi --resource apache-nifi=<PATH to file>
```
To run Apache NiFi in a cluster, a relation must be made between Apache NiFi and Apache Zookeeper:
```
juju add-relation apache-nifi zookeeper
```
If you want to run Apache NiFi in a standalone configuration, the relation must be removed:
```
juju remove-relation apache-nifi zookeeper
```
<p>
**When the relation is removed, Apache NiFi does not start automatically!** This is to prevent problems with multiple
instances of Apache NiFi to run on the same dataset.
</p>
<p>
After deploy or add-relation, the user interface off Apache NiFi is accessible through your browser at <ip-address>:<nifi-port>. The port defaults to 8080. However, it can take up to 2 minutes after install before the user interface is accessible, or all the nodes in the cluster are visible in the user interface.
</p>
# Bugs
Report bugs on <a href="https://github.com/IBCNServices/tengu-charms/issues">Github</a>
# Author
Mathijs Moerman <a href="mailto:mathijs.moerman@qrama.io">mathijs.moerman@qrama.io</a>
