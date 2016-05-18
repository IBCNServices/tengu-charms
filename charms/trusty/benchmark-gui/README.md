# Overview

Benchmark GUI, for Charm Benchmarking, is a set of Juju Charms to repeatedly run benchmarks across multiple different substrates (bare metal[x86, POWER, ARM], public, private cloud) and continually improve on the services and benchmarks. Benchmark GUI is able to perform the following tasks:
- determine which benchmarks can be run for a given environment
- list available benchmarks to run
- run and track benchmarks
- collect performance data
- report on results
- compare benchmark runs

The main intent is to allow folks interested in a given workload to repeatedly run a benchmark across multiple substrates, and enable quick experimentation to improve the service's performance. Benchmark GUI takes care of the benchmarking infrastructure so the focus is on the science of tuning.

The Benchmark GUI charm is the main way the user will interact with the benchmarking environment. The Benchmark GUI charm provides a GUI that allows the user to perform the above mentioned actions.

# Getting Started

This guide aims to lead a user from zero to benchmarking. Prerequisites include:
- Knowledge of [Juju](https://jujucharms.com) and how it [works](https://jujucharms.com/docs/stable/getting-started)
- [Latest Juju version recommended](https://jujucharms.com/get-started), Juju 1.24 minimum
- A [Juju bootstrapped](https://jujucharms.com/docs/stable/getting-started) environment

# Configuring Benchmark GUI

Assuming you already have a Juju environment [bootstrapped](https://jujucharms.com/docs/stable/charms) you will first need to deploy the Benchmark GUI and benchmark-collector charms into your environment.

    juju deploy local:trusty/benchmark-gui
    juju deploy local:trusty/benchmark-collector

The Benchmark GUI charm needs to communicate with the Juju API server. In order to do that, you'll need to set the juju-secret configuration key. This is the "password" field in any bootstrapped environments, .jenv file, or the `admin-secret` key in your environments.yaml file. One way to achieve this is to run the following command:

    grep "password" ~/.juju/environments/$(juju switch).jenv | awk '{ print $2 }'

Then set the juju-secret key for Benchmark GUI by doing the following.

    juju set benchmark-gui juju-secret=<admin-secret>

Once that's set, the Benchmark GUI charm will finish it's configuration and you'll be able to browse to http://ip-address:9000/ to view and compare the benchmark metrics.

Stand up your target environment. For example, if we wanted to benchmark a mediawiki deployment, we would do something like this:

    juju deploy mediawiki
    juju deploy mysql
    juju deploy siege

    juju add-relation mysql mediawiki:db
    juju add-relation mediawiki siege

    # Setup the subordinate relation between benchmark-collector and the services to be benchmarked
    juju add-relation benchmark-collector mediawiki
    juju add-relation benchmark-collector mysql

    juju add-relation benchmark-gui benchmark-collector:collector

    # Relate the benchmark-aware charm to benchmark-gui so we can launch benchmarks from the benchmark UI
    juju add-relation benchmark-gui siege

# Basic use of the UI

The Benchmark GUI dashboard provides you with a high-level view of benchmark statistics, including:
- The name of the service:benchmark.
- It's state; running, queued, errored, or complete.
- The unit or service the benchmark was run against.
- The composite result; a single representative unit to judge the benchmark by.
- The length of time it took for the benchmark to run, including any standing up or down required by the benchmark.
- When the benchmark was launched.

You can launch actions directly from the Benchmark GUI dashboard, rather than using the `juju action` command. Clicking on the "Launch Benchmark" button will give you a form where you can select the available benchmarks from any benchmark-enabled charm. Select the benchmark you'd like to run, choose the unit(s) to run against, the tag(s) you'd like associated with this run, and any configuration options and press "Launch". You'll then be returned to the dashboard, where you can monitor the status of the benchmark.

## Benchmark Details

Clicking on a benchmark name will take you to a page with the parameters, results, and collected metrics from that benchmark run.

## Comparison

When you have more than one of the same type of benchmark, you can compare two or more benchmarks.

Moving your mouse over a benchmark will backlight all benchmarks of the same type and highlight the best scoring benchmark.

Use the selector to choose benchmarks to compare. Once two or more benchmarks are selected, the "Launch Benchmark" button will offer a drop-down option to compare.


## Importing/Exporting data

You can export and import benchmark data in two ways:
- Via buttons on the Benchmark GUI dashboard
- Via API endpoints

### Exporting

The "Export Data" button will download a JSON file of all the benchmark data in the Benchmark GUI database. This includes benchmark data generated in the current environment as well as data previously imported from other environments.

The exported file includes benchmark data, metric data, graph data, profile data, and comparison data. The file may be saved and later imported into another Benchmark GUI environment.

    # API Export
    curl http://ip-address:9000/api/export > /tmp/export.json

### Importing

The "Import Data" button will display a file upload form. Upload a JSON file that was previously exported from a Benchmark GUI environment. Multiple files may be imported one after another, making it possible to consolidate data from many different Benchmark GUI environments.

    # API Import
    curl -X POST http://ip-address:9000/api/import -d @/tmp/export.json --header "Content-Type: application/json"

# How to write benchmarks

Benchmarks are written as [Juju Actions](https://jujucharms.com/docs/stable/actions) on charms. Benchmarks are typically either an [action](https://jujucharms.com/docs/stable/actions) on the service you wish to benchmark, a service which solely does benchmarking (load generation), or a subordinate which, when related, installs a benchmark suite.

Please refer to the [Juju Docs](https://jujucharms.com/docs/devel/authors-charm-benchmarks) for further details on developing benchmarks for Juju Charms.

# Charms with benchmarks
 - [siege](https://github.com/juju-solutions/siege)
 - [cassandra](https://github.com/juju-solutions/cassandra)
 - [hadoop](https://code.launchpad.net/~aisrael/charms/trusty/apache-hadoop-client/benchmarks)
 - [pts](https://github.com/phoronix-test-suite/phoronix-test-suite/tree/master/deploy/juju/trusty/pts)
 - [mongodb](https://jujucharms.com/mongodb)
 - [mysql-benchmark](https://github.com/juju-solutions/mysql-benchmark) (works against mysql, percona, and mariadb)
 - [Rally](https://jujucharms.com/u/marcoceppi/rally/trusty/0)
