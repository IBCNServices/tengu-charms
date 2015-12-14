#!/usr/bin/python
# pylint: disable=c0111,c0103
import setup # pylint: disable=F0401
import sys
setup.pre_install()
import subprocess
from netifaces import AF_INET
import netifaces
import netaddr

from charmhelpers.core import hookenv

BRIDGECONFIG = """auto lxcbr0
iface lxcbr0 inet dhcp
    bridge_ports """


# Hooks
HOOKS = hookenv.Hooks()

@HOOKS.hook('upgrade-charm')
def upgrade_charm():
    hookenv.log('Updating tengu-instance-admin')
    install()

@HOOKS.hook('install')
def install():
    config = hookenv.config()
    net_addr = config['network']
    network = netaddr.IPNetwork(net_addr)
    interface = None
    for interface in netifaces.interfaces():
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet and af_inet[0].get('addr'):
            addr = netifaces.ifaddresses(interface)[AF_INET][0]['addr']
            if netaddr.IPAddress(addr) in network:
                found = True
                break
    assert found
    bridgeconfig = "{} {}\n".format(BRIDGECONFIG, interface)
    with open("/etc/network/interfaces", 'r+') as sudoers_file:
        content = sudoers_file.read()
        if bridgeconfig in content:
            print "present"
            exit(1)
        print "after"
        sudoers_file.write(bridgeconfig)
    try:
        subprocess.check_output(['sudo', 'ifup', 'lxcbr0'])
    except subprocess.CalledProcessError as exception:
        print exception.output
    hookenv.status_set('active', 'Ready')


# Hook logic
if __name__ == "__main__":
    HOOKS.execute(sys.argv)
