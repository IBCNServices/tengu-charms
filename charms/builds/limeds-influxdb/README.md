# LimeDS InfluxDB installable

This Charm adds a InfluxDB segment to LimeDS that you can use to talk to InfluxDB.

# Usage

```bash
# Deploy InfluxDB
juju deploy cs:~chris.macnaughton/influxdb-4
# Deploy the LimeDS bundle
juju deploy cs:~tengu-team/limeds-core
# Deploy the LimeDS InfluxDB connector
juju deploy cs:~tengu-tean/limeds-influxdb

# Connect limeds-influxdb to limeds and to influxdb
juju add-relation limeds limeds-influxdb
juju add-relation mongoDB limeds-influxdb

# Expose the Docker container where LimeDS is running
juju expose docker
```

Watch it being deployed using `watch -c juju status --color` (close using <kbd>ctrl</kbd>-<kbd>c</kbd>).

```
App          Version  Status  Scale  Charm             Store       Rev  OS      Notes
docker                active       1  docker           jujucharms    3  ubuntu  exposed
limeds                active       1  limeds           jujucharms    1  ubuntu
limeds-influxdb       active       1  limeds-influxdb  jujucharms    1  ubuntu
influxdb              unknown      1  influxdb         jujucharms   37  ubuntu

Unit                 Workload  Agent      Machine  Public address  Ports                                    Message
docker/0*            active    idle       38       54.165.156.82   32768/tcp                                Ready
limeds/0*            active    idle       38       54.165.156.82                                            Ready (ibcndevs/limeds)
  limeds-influxdb/0* active    idle                54.165.156.82                                            Ready (1 units)
influxdb/0*          unknown   idle       39       107.23.144.223  
```

After deployment, go to `http://<docker-url>:<docker-port>/editor` and import the segment to your slice.


# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](https://tengu.io), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
