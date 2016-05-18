#!/usr/bin/python3
# Copyright (C) 2016  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=c0111,c0103
import subprocess
from collections import defaultdict

import netifaces
from netifaces import AF_INET
import netaddr

# Charm pip dependencies
from charmhelpers import fetch
from charmhelpers.core import hookenv
from charms.reactive import when_not, set_state, remove_state


BRIDGECONFIG = """# Managed by Juju lxc-networking <
auto lxcbr0
iface lxcbr0 inet static
    bridge_ifaces {interface}
    bridge_ports {interface}
    address {address}
    netmask {netmask}
# Managed by Juju lxc-networking >
"""
""" sudo apt-get install vlan
sudo modprobe 8021q
sudo vconfig add eth0 10
sudo ip addr add 10.0.0.6/24 dev eth0.10
sudo ip link set up eth0.10

"""

@when_not('lxc-networking.active')
def install():
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages(
        ['isc-dhcp-server', 'iptables-persistent']
    ))
    config = hookenv.config()
    net_addr = config['network']
    network = netaddr.IPNetwork(net_addr)
    interface = None
    address = None
    netmask = None
    found = False
    for interface in netifaces.interfaces():
        if interface == 'lxcbr0':
            hookenv.status_set(
                'active',
                'Ready (untouched)')
            exit()
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet and af_inet[0].get('addr'):
            address = netifaces.ifaddresses(interface)[AF_INET][0]['addr']
            netmask = netifaces.ifaddresses(interface)[AF_INET][0]['netmask']
            if netaddr.IPAddress(address) in network:
                found = True
                break
    if not found:
        hookenv.status_set(
            'blocked',
            'Cannot find interface that is connected to network {}.'.format(network))
        return
    bridgeconfig = BRIDGECONFIG.format(
        interface=interface,
        address=address,
        netmask=netmask
    )
    with open("/etc/network/interfaces", 'r+') as ifaces_file:
        content = ifaces_file.read()
        import re
        s = re.compile(
            r'# Managed by Juju lxc-networking <\n.*# Managed by Juju lxc-networking\n>',
            re.MULTILINE | re.DOTALL)
        content = re.sub(s, '', content)
        content = content + bridgeconfig
        ifaces_file.write(bridgeconfig)
    try:
        subprocess.check_call(['ifdown', 'lxcbr0'])
    except subprocess.CalledProcessError as exception:
        print(exception.output)
    try:
        subprocess.check_call(['ifup', 'lxcbr0'])
    except subprocess.CalledProcessError as exception:
        remove_state('lxc-networking.active')
        print(exception.output)
        raise exception
    hookenv.status_set('active', 'Ready')
    set_state('lxc-networking.active')


def parse_interfaces():
    """ Parses interfaces file into a dict:
        {
            auto: <auto line or no line>,
            iface: <iface line>,
            address: <address line>,
            netmask: <netmask line>,
            bridge_ifaces: <bridge_ifaces line>,
            bridge_ports: <bridge_ports line>,
            body: [array of other statements],
        }
    """
    curr_if = None
    interfaces = defaultdict(lambda: {
        'auto': '',
        'body': [],
    })
    with open('/etc/network/interfaces', 'r') as if_file:
        content = if_file.readlines()
    for line in content:
        line = line.lstrip().rstrip()
        if line.startswith(('auto', 'iface')): # One of the two possible headers
            curr_if = line.split()[1]
            interfaces[curr_if][line.split()[0]] = line
        elif line.startswith(('address', 'netmask', 'bridge_ifaces', 'bridge_ports')):
            interfaces[curr_if][line.split()[0]] = line
        else:
            if curr_if:
                interfaces[curr_if]['body'].append(line)
    return interfaces
