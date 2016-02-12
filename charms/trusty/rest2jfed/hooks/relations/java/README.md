# Overview

This interface layer handles the communication with Java related services via
the `java` interface protocol.  It sets two states when appropriate:

  * `{relation_name}.connected` indicates that a Java relation is present
  * `{relation_name}.ready` indicates that Java is installed and ready

The charm implementing this relation (e.g., [openjdk][]) will install and
configure the Java environment. It also sets two pieces of relation data:

  * `java-home` is equivalent to the $JAVA_HOME environment variable
  * `java-version` is the numeric version string (e.g. "1.7.0_85")

The charm consuming this relation (e.g., [ubuntu-java][]) will use the above
relation data to configure its Java based service.


# Example Usage

An example of a charm using this interface would be:

```python
@when('java.connected')
@when_not('java.installed')
def install():
    status_set('maintenance', 'Installing JRE')
    java.install_jre()
    reactive.set_state('java.installed')
    hookenv.status_set('active', 'JRE is installed')

@when('java.connected', 'java.installed')
def configure():
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
