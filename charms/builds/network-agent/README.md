# Overview

This Charm manages a network. It will do the following things to the network it manages:


 - Configure itself as NAT gateway
 - Forward the ports requested in the `port-forwards` config option and from the `port-forwards` relations.
 - Create a dhcp-server ([ISC dhcp-server](https://www.isc.org/downloads/dhcp/)) if there isn't one present. Tell the clients he is the default gateway if there isn't one present on the network.

It will also display its public IP (or the source ip of the default-gateway interface if no public ip was found).

*Note: this charm requires a working connection to the internet*

# Usage

To add te gateway to your environment:

    juju deploy cs:~tengu-bot/trusty/network-agent

# Configuration

 -  **managed-network**: Network the dhcp-server should broadcast to. It will decide what interface to broadcast to based on this network. *default: '192.168.14.0/24'*

 -  **dhcp-range**: Range that dhcp-server should distribute. *default: '192.168.14.50 192.168.14.253'*

 -  **port-forwards**: This option takes a list of json objects. Each object represents a requested port forward. *default: "[]"*

 Example configuration:

 ```
 network-agent:
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
