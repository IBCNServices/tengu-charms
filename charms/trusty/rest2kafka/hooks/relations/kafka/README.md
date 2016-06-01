# Overview

This interface layer handles the communication between Kafka and its
clients. The provider part of this interface provides the Kafka service.
The consumer part requires the existence of a provider to function.


# Usage

## Provides

Charms providing the Apache Kafka service *provide* this interface. This
interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The provider has been related to a client,
  though the client service may not be available yet. At this point, the
  provider should broadcast Kafka configuration details using:

    * `send_port(self, port)`
    * `send_zookeepers(self, zk_host_port_pair_list)`


  * `{relation_name}.ready`  Kafka configuration details have been sent. The
  provider and client should now be able to communicate.


Kafka provider example:

```python
@when('client.joined', 'zookeeper.ready')
def serve_client(client, zookeeper):
    client.send_port(get_kafka_port())
    client.send_zookeepers(zookeeper.zookeepers())
```

## Requires

Clients *require* this interface to connect to Apache Kafka. This interface
layer will set the following states, as appropriate:

  * `{relation_name}.joined` The client charm has been related to a Kafka
  provider. At this point, the charm waits for Kafka configuration details.

  * `{relation_name}.ready`  Kafka is now ready for clients. The client
  charm should get Kafka configuration details using:

    * `kafkas()`
    * `zookeepers()`


Kafka client example:

```python
@when('kafka.joined')
@when_not('kafka.ready')
def wait_for_kafka(kafka):
    hookenv.status_set('waiting', 'Waiting for Kafka to become ready')


@when('kafka.ready')
@when_not('myservice.configured')
def configure(kafka):
    for kafka_unit in kafka.kafkas():
        add_kafka(kafka_unit['host'], kafka_unit['port'])
    set_state('myservice.configured')
```


# Contact Information

- <bigdata@lists.ubuntu.com>
