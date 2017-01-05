# Overview

This interface layer handles the communication between a Spark client and Spark.

# Usage

## Provides

The Spark deployment is provided by the Spark charm. this charm has to
signal to all its related clients that has become available.

The interface layer sets the following state as soon as a client is connected:

  * `{relation_name}.joined` The relation between the client and Spark is established.

The Spark provider can signal its availability through the following methods:

  * `set_spark_started()` Spark is available.

  * `clear_spark_started()` Spark is down.

An example of a charm using this interface would be:

```python
@when('spark.started', 'client.related')
def client_present(client):
    client.set_installed()


@when('client.related')
@when_not('spark.started')
def client_should_stop(client):
    client.clear_installed()
```


## Requires

This is the side that a Spark client charm (e.g., Zeppelin)
will use to be informed of the availability of Spark.

The interface layer will set the following state for the client to react to, as
appropriate:

  * `{relation_name}.joined` The client is related to Spark and is waiting for Spark to become available.

  * `{relation_name}.ready` Spark is ready to be used.

An example of a charm using this interface would be:

```python
@when('zeppelin.installed', 'spark.ready')
@when_not('zeppelin.started')
def configure_zeppelin(spark):
    hookenv.status_set('maintenance', 'Setting up Zeppelin')
    zepp = Zeppelin(get_dist_config())
    zepp.start()
    set_state('zeppelin.started')
    hookenv.status_set('active', 'Ready')


@when('zeppelin.started')
@when_not('spark.ready')
def stop_zeppelin():
    zepp = Zeppelin(get_dist_config())
    zepp.stop()
    remove_state('zeppelin.started')
```


# Contact Information

- <bigdata@lists.ubuntu.com>

