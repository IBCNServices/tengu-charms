# Overview

This interface layer handles the communication between a Hive client and Hive.

# Usage

## Provides

The Hive deployment is provided by the Hive charm. this charm has to
signal to all its related clients that has become available.

The interface layer sets the following state as soon as a client is connected:

  * `{relation_name}.joined` The relation between the client and Hive is established.

The Hive provider can signal its availability through the following methods:

  * `set_ready()` Hive is available.

  * `clear_ready()` Hive is not available.

  * `send_port()` Sends port over relation

An example of a charm using this interface would be:

```python
@when('hive.started', 'client.related')
def client_present(client):
    client.set_ready()


@when('client.related')
@when_not('hive.started')
def client_should_stop(client):
    client.clear_ready()
```


## Requires

This is the side that a Hive client charm (e.g., HUE)
will use to be informed of the availability of Hive.

The interface layer will set the following state for the client to react to, as
appropriate:

  * `{relation_name}.joined` The client is related to Hive and is waiting for Hive to become available.

  * `{relation_name}.ready` Hive is ready to be used.

An example of a charm using this interface would be:

```python
@when('hue.installed', 'hive.ready')
@when_not('hue.started')
def configure_hue(hive):
    hookenv.status_set('maintenance', 'Setting up Hue')
    hue = Hue(get_dist_config())
    hue.start()
    set_state('hue.started')
    hookenv.status_set('active', 'Ready')


@when('hue.started')
@when_not('hive.ready')
def stop_hue():
    hue = Hue(get_dist_config())
    hue.stop()
    remove_state('hue.started')
```


# Contact Information

- <bigdata@lists.ubuntu.com>

