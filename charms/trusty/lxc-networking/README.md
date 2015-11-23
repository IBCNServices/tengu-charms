# Overview

This Charm configures the unit so LXC containers are bridged directly to the given network, allowing them to dhcp the network the host is connected to for ip adresses.

This is achieved by creating the lxcbr0 interface and configuring it to connect directly to the interface of the given network. Default LXC containers are connected to this bridge; connecting them to the eth0 interface.

# Usage

Deploy charm onto unit:

    juju deploy lxc-networking --to 0

Deploy Charm in container on unit:

    juju deploy wordpress --to lxc:0

This will create container 0/lxc/0 which is connected to the eth0 interface of machine 0. You can verify this by running `watch juju status --format tabular`. You should see wordpress/0 get a public-address from the dhcp server.

# Configuration

No config options available

# Contact Information

merlijn.sebrechts@gmail.com
