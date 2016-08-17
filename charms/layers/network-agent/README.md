# Overview

This Charm manages a network. It will configure itsel



This Charm configures a server to act as an [ISC dhcp-server](https://www.isc.org/downloads/dhcp/). If the dhcp broadcast interface is different from the interface the default gateway is on, then this Charm configures the host as a NAT gateway for the dhcp network.

# Usage

To add te gateway to your environment:

    juju deploy dhcp-server

# Configuration

 -  **dhcp-network**: Network the dhcp-server should broadcast to. It will decide what interface to broadcast to based on this network. *default: '192.168.14.0/24'*

 -  **dhcp-range**: Range that dhcp-server should distribute. *default: '192.168.14.50 192.168.14.253'*

 -  **port-forwards**: This option takes a list of json objects. Each object represents a requested port forward. *default: "[]"*

 Example configuration:

 ```
 dhcp-server:
    port-forwards: |
      [{
        "public_port": "9999",
        "private_port": "21",
        "private_ip": "192.168.14.2",
        "protocol": "tcp"
      },
      {
        "public_port": "5001",
        "private_port": "5000",
        "private_ip": "192.168.14.152",
        "protocol": "tcp"
      }]
 ```

 -  **portrange**: The start port of the range to use for dynamically assigning port forwards. When a Charm requests a port forward, it will be assigned a port starting from the portrange. *default: 29000*


# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
 - Part of globe icon made by [Zurb](http://www.flaticon.com/authors/zurb) from [www.flaticon.com](http://www.flaticon.com) licensed as [Creative Commons BY 3.0](http://creativecommons.org/licenses/by/3.0/)
