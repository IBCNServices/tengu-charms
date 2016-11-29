# Overview

This layer installs and configures the juju-client for Juju 2.0. It can be used by Charms that want to manage Juju environments.


# Usage

The .yaml files defined in config must be parsed in Base64Encoding. These cannot be uploaded using resources, since this would make them accessible to all other charms on the controller (Resources can be uploaded to a local Juju controller, where only charms from that controller can access the resources, source <a href="https://jujucharms.com/docs/stable/developer-resources">https://jujucharms.com/docs/stable/developer-resources</a>

You can react to the states `juju.installed` and `juju.upgraded`. The [`tengu-intance-admin`](https://github.com/IBCNServices/tengu-charms/tree/master/charms/layers/tengu-instance-admin) is an example of al layer that uses this layer.


# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
