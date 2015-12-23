# Overview

This charm provides [ISC DHCP server](https://www.isc.org/downloads/dhcp/). This charms target platform is Ubuntu Trusty 14.04.

# Usage

To add isc-dhcp to your environment:

    juju deploy isc-dhcp


# Configuration

sysctl net.ipv4.conf.all.rp_filter=0
sysctl net.ipv4.conf.default.rp_filter=0
sysctl net.ipv4.conf.tun0.rp_filter=0
sysctl net.ipv4.conf.wlp3s0.rp_filter=0

# Contact Information

https://launchpad.net/charms/+source/isc-dhcp
