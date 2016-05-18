# Overview

This interface layer handles the communication with the Benchmark GUI via the
`benchmark` interface protocol.


# Usage

## Requires

The Benchmark GUI requires this interface to be provided by charms which have
benchmarks.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The relation is established, but the charm may not
    have provided any benchmark information.

  * `{relation_name}.registered` The charm has registered a list of benchmarks.
    The list of benchmarks can be accessed via the `registered()`.

For example, the GUI would handle the `benchmark.registered` state with something like:

```python
@when('benchmark.installed', 'benchmark.registered')
def register_benchmarks(benchmark):
    for service, benchmarks in benchmark.registered().items():
        hookenv.log('benchmarks received: %s' % benchmarks)
        requests.post(
            'http://localhost:9000/api/services/{}'.format(service),
            data=json.dumps({'benchmarks': benchmarks}),
            headers={
                'content-type': 'application/json'
            }
        )
```


## Provides

A charm providing this interface is providing benchmarks to the Benchmark GUI.

This interface layer will set the following states, as appropriate:

  * `{relation_name}.joined` The Benchmark GUI has been related.  The charm
    should call the `register(*benchmarks)` method to register a list of
    benchmarks with the GUI (note: this can either be passed one or more
    strings, e.g., `register('foo', 'bar')` or it can be passed a list,
    e.g., `register(['foo', 'bar'])`).

Example:

```python
@when('benchmark.joined')
def register_benchmarks(benchmark):
    benchmark.register('pagerank', 'trianglecount', 'sql')
```


# Contact Information

- <bigdata@lists.ubuntu.com>
