# Overview

This interface layer handles the communication between Apache Zookeeper and its
clients. The provider end of this interface provides the Zookeeper service.
The consumer part requires the existence of a provider to function.


# Usage

## Provides

Charms providing the Apache Zookeeper service *provide* this interface. This
interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The provider has been related to a client,
  though the client service may not be available yet. At this point,
  the provider should broadcast Zookeeper configuration details using:

    * `send_port(port, rest_port)`


  * `{relation_name}.ready`  Zookeeper configuration details have been sent.
  The provider and client should now be able to communicate.


Zookeeper provider example:

```python
@when('client.joined')
@when_not('client.ready')
def send_config(client):
    client.send_port(get_zookeeper_port(), get_zookeeper_rest_port())
```


## Requires

Clients *require* this interface to connect to Apache Zookeeper. This interface
layer will set the following states, as appropriate:

  * `{relation_name}.joined` The client charm has been related to a Zookeeper
  provider. At this point, the charm waits for Zookeeper configuration details.

  * `{relation_name}.ready`  Zookeeper is now ready for clients. The client
  charm should get Zookeeper configuration details using:

    * `zookeepers()` returns a list of zookeeper 
                     {host: xyz, port: n, rest_port: m} dicts


Zookeeper client example:

```python
@when('zookeeper.joined')
@when_not('zookeeper.ready')
def wait_for_zookeeper(zookeeper):
    hookenv.status_set('waiting', 'Waiting for Zookeeper to become available')


@when('zookeeper.ready')
@when_not('myservice.configured')
def configure(zookeeper):
    for zk_unit in zookeeper.zookeepers():
        add_zookeeper(zk_unit['host'], zk_unit['port'])
    set_state('myservice.configured')
```


# Contact Information

- <bigdata@lists.ubuntu.com>
