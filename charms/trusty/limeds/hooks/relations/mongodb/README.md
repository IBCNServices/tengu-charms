# Overview

This interface handles the communication between a MongoDB client and a MongoDB server.

# Usage

## Requires

This is the side that a MongoDB client charm will use to be informed of the availability of MongoDB.

The interface layer will set the following state for the client to react to, as
appropriate:

  * `{relation_name}.database.connected` The client is related to MongoDB and is waiting for MongoDB to become available.

  * `{relation_name}.database.available` MongoDB is ready to be used.

An example of a charm using this interface would be:

```python
@when('limeds.installed', 'mongodb.available')
@when_not('limeds.started')
def configure_limeds(mongodb):
  hookenv.status_set('maintenance', 'Setting up LimeDS MongoDB relation')
    configure_limeds_mongodb(mongodb)
    host.service_start('limeds')
    set_state('limeds.started')
    hookenv.status_set('active', 'Ready')


@when('limeds.started')
@when_not('mongodb.available')
def stop_limeds():
    stop_limeds()
    remove_state('limeds.started')
```




## Provides

The provides side of the interface still hasn't been developed yet.

# Contact Information

- "Mattyw" <gh@mattyw.net>
