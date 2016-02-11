# Overview

This Charm configures a server to act as an [ISC dhcp-server](https://www.isc.org/downloads/dhcp/) and a NAT gateway.

# Usage

To add te gateway to your environment:

    juju deploy dhcp-server

# Configuration

 -  **port-forwards**: This option takes a list of json objects. Each object represents a requested port forward.

Example configuration:

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

# Contact Information

Maintainer: Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
