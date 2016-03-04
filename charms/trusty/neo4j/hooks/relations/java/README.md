# Overview

This interface layer handles the communication between charms needing a Java
runtime (JRE or JDK) and subordinate charms which deliver that runtime.


# Usage

## Charms needing a Java runtime

Charms needing a Java runtime must `provide` a relation endpoint using the
`java` interface protocol in their `metadata.yaml` file and `include` this
interface layer in their `layer.yaml` file.  Then, they can watch for the
following reactive states:

  * `{relation_name}.connected` indicates that a Java relation is present
    (this is mainly used for reporting if the relation is missing, via status)
  * `{relation_name}.ready` indicates that Java is installed and ready

The relation also provides the following methods for getting information about
the Java runtime:

  * `java_home()` provides the path that the `JAVA_HOME` env var should be set to
  * `java_version()` provides the major version of Java that was installed

An example of how a charm might use this would be:

```python
@when_not('java.ready')
def missing_java():
    hookenv.status_set('blocked', 'Missing JRE')

@when('java.ready')
@when_not('mysoftware.installed')
def install_software(java):
    mysoftware.install(java.java_home(), java.java_version())
    set_state('mysoftware.installed')
    hookenv.status_set('active', 'Ready')
```


## Charms delivering a Java runtime

Charms delivering a Java runtime must be subordinate, and they must `require`
a relation endpoint using the `java` interface protocol in their `metadata.yaml`
file and `include` this interface layer in their `layer.yaml` file.  Then, they
can watch for the following reactive states:

  * `{relation_name}.connected` indicates that a Java relation is present.
    The charm should then perform the installation and call the following methods
    to provide the necessary information about the Java runtime that was installed:
    * `set_ready(java_home, java_version)`
    * `set_version(java_version)` (for upgrades)

An example of how a charm might use this would be:

```python
@when('java.connected')
@when_not('java.installed')
def install(client):
    status_set('maintenance', 'Installing JRE')
    java.install_jre()
    client.set_ready(java.get_home(), java.get_version())
    reactive.set_state('java.installed')
    hookenv.status_set('active', 'JRE is installed')

@when('java.connected', 'java.installed')
def configure(client):
    # update /etc/environment, call update-alternatives, etc
    java.configure_jre()
    hookenv.status_set('active', 'JRE is ready')

@when_not('java.connected')
@when('java.installed')
def uninstall():
    java.uninstall_jre()
    reactive.remove_state('java.installed')
    hookenv.status_set('blocked', 'No JRE available')
```


# Contact Information

- <bigdata@lists.ubuntu.com>


# OpenJDK

- [OpenJDK](http://openjdk.java.net/) home page


[openjdk]: https://jujucharms.com/u/kwmonroe/openjdk
[ubuntu-java]: https://jujucharms.com/u/kwmonroe/ubuntu-java
