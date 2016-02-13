#!/usr/bin/python3
# pylint: disable=c0111,c0103
import subprocess
import netifaces
from netifaces import AF_INET
import netaddr

# Charm pip dependencies
from charmhelpers.core import hookenv
from charms.reactive import hook, set_state, remove_state


BRIDGECONFIG = """# Managed by Juju lxc-networking <
auto lxcbr0
iface lxcbr0 inet dhcp
    bridge_ifaces {interface}
    bridge_ports {interface}
    address {address}
    netmask {netmask}
# Managed by Juju lxc-networking >"""


@hook('config-changed')
def install():
    config = hookenv.config()
    net_addr = config['network']
    network = netaddr.IPNetwork(net_addr)
    interface = None
    address = None
    netmask = None
    for interface in netifaces.interfaces():
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
