# Overview
Apache NiFi is an easy, powerful, and reliable system to process and distribute data. More info can be found [on the Apache Nifi website](https://nifi.apache.org).

# Usage
This charm uses JuJu 2 to access the Apache Nifi tarball. Apache NiFi depends on Java 8. This is automatically installed if necessary.

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

When Apache NiFi is running in a cluster, it will detect changes in the Apache Zookeeper setup and react to them if necessary. Apache NiFi can be changed to run in a standalone configuration when it's running in a cluster by removing the relation with Apache Zookeeper:

```
juju remove-relation apache-nifi zookeeper
```

**WARNING! Remove all but one unit before removing the relation with Zookeeper** This is to prevent problems with multiple instances of Apache NiFi to run on the same dataset.

After deploy or add-relation, the user interface of Apache NiFi is accessible through your browser at `<ip-address>:<nifi-port>`. The port defaults to 8080. However, it can take up to 2 minutes after install before the user interface is accessible, or all the nodes in the cluster are visible in the user interface.

# Configuration options

The following configuration options are available:

 - **`nifi-port`** Defaults to 8080. The user interface is accessible on this port.
 - **`cluster-port`** Defaults to 8517. The nodes communicate to the Cluster Coordinator on this port.
 - **`java-major** Defaults to 8. **This may not be set to a lower version!**

All other configuration options have to be set manually in the Apache NiFi configuration files. More info can be in [on the Apache Nifi developer guide](https://nifi.apache.org/developer-guide.html).

# Bugs

Report bugs on [the Apache NiFi layer Github repository](https://github.com/IBCNServices/layer-Apache-NiFi/issues)

# Author

Mathijs Moerman <mathijs.moerman@qrama.io>
