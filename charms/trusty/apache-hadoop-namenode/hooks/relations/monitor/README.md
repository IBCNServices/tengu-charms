# Overview

This interface layer handles the communication between any service and a service that
provides monitoring facilities (currently only Ganglia).


# Usage

## Reporting Metrics

Charms that gather and report metrics to a monitoring service must `provide`
a relation using the `monitor` interface and add `interface:monitor` to the
`includes` section of their `layer.yaml` file.

This interface layer will set the following state, as appropriate:

  * `{relation_name}.joined` The relation to the monitoring service has been
    established. The charm can retrieve information about the monitoring service via:

    * `endpoints()`  Returns a list of dicts containing info about the
      monitoring services.  Each dict will contain a `host` address and a `port`.

An example use of this would be:

```python
@when('ganglia.available')
def setup_monitoring(ganglia):
    register_monitor(ganglia.endpoints())
```

## Aggregating Metrics

Charms that act as a monitoring service which aggregate and provide insight into
collected metrics must `require` a relation using the `monitor` interface and
add `interface:monitor` to the `includes` section of their `layer.yaml` file.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` One or more services have connected to send metrics
    The charm can then get information about the the connected services via:

    * `endpoints()` Returns a list of addresses for the connected services

# Contact Information

- <bigdata@lists.ubuntu.com>
