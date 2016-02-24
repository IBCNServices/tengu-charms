# Overview

This Charm enables networking of LXC containers on the Juju manual provider. This is done by bridging the network of the containers to the network specified in the config. This network is required to have a dhcp-server that gives out ip addresses with an indefinite lease. When a container boots up, it will get an IP address from the dhcp-server.

**After this Charm entered the 'Ready' state, you cannot change the network it will connect the containers to.**

# Usage

Create config file `config.yaml`:

  lxc-networking:
    network: 192.168.14.0/24

Deploy charm onto the container host machines:

    juju deploy local:lxc-networking --config config.yaml --to 0

Deploy a dhcp-server to one of the host machines:

    juju deploy local:dhcp-server --to 0

Deploy a Charm in a container on one of the container hosts:

    juju deploy wordpress --to lxc:0

This will create container 0/lxc/0 which is connected to the 192.168.14.0/24 interface of machine 0. You can verify this by running `watch juju status --format tabular`. You should see wordpress/0 get a public-address from the dhcp server.

# Configuration

    network:
      type: string
      description: Network to bridge lxc containers to
      default: 192.168.14.0/24


# How does it work?

This Charm works as follows:

1. The Charm searches for the interface that is connected to the network specified in the `network` config options.
2. The Charm creates the `lxcbr0` interface and bridges it to the interface found in step *1.*.
3. The Charm gives `lxcbr0` the IP of its bridged interface as a static IP.

The lxcbr0 configuration is set in `/etc/network/interfaces`.

# Contact Information

merlijn.sebrechts@gmail.com
