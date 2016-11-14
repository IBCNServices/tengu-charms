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
# source: https://www.howtoforge.com/nat_iptables
# pylint: disable=c0111,c0103,c0301,c0325
# https://unix.stackexchange.com/questions/4420/reply-on-same-interface-as-incoming
import os
import json
import subprocess
from ipaddress import IPv4Network, IPv4Address

from charmhelpers.core import hookenv, templating, host, unitdata
from charmhelpers.core.hookenv import config
from charmhelpers import fetch
from charms.reactive import hook, when, when_not, when_all, set_state, remove_state

# modules from Pip dependencies
from netifaces import AF_INET
import netifaces

# Own modules
from iptables import update_port_forwards, configure_nat_gateway, get_gateway_source_ip

@hook('upgrade-charm')
def upgrade_charm():
    remove_state('dhcp-server.installed')
    remove_state('dhcp-server.configured')
    remove_state('dependencies.installed')


@when_not('dependencies.installed')
def install_iptables_persistent():
    hookenv.log('Installing iptables-persistent')
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages(
        ['iptables-persistent', 'nmap']
    ))
    set_state('dependencies.installed')


@when(
    'config.changed.managed-network'
)
@when('dependencies.installed')
def configure():
    hookenv.log('Configuring isc-dhcp')
    managed_network = IPv4Network(config()["managed-network"])
    # We know what network we should be managing. This IPNetwork object has the
    # following properties:
    #   .ip            # Original ip from config value
    #   .network       # network ip
    #   .netmmask
    #   .broadcast_address
    #
    # What we don't know is what interface this network is connected to. The
    # following code tries to find out:
    #   1. what interface is connected to that network
    #   2. what the ip is of that interface
    #   3. what other interfaces we have, ie interfaces that are unmanaged.
    #   4. what our public ip is
    #
    # Then we do two sanity checks: the broadcast and netmask of that interface
    # must be the same as for the managed network.
    #
    mn_iface = None
    mn_iface_ip = None
    unmanaged_ifs = []
    public_ip = None
    for interface in netifaces.interfaces():
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet and af_inet[0].get('broadcast'):
            addr = IPv4Address(netifaces.ifaddresses(interface)[AF_INET][0]['addr'])
            if not addr.is_private: # Can't use is_global in 14.04 because of: https://bugs.python.org/issue21386
                # We found #4!
                public_ip = str(addr)
                public_if = interface
            if addr in managed_network:
                # We found #1 and #2 !
                mn_iface = interface
                mn_iface_ip = str(addr)
                # Sanity check
                assert(str(managed_network.broadcast_address) == netifaces.ifaddresses(interface)[AF_INET][0]['broadcast'])
                assert(str(managed_network.netmask) == netifaces.ifaddresses(interface)[AF_INET][0]['netmask'])
            else:
                # to find #3
                unmanaged_ifs.append(interface)
    if not public_ip:
        # No public ip found, so we'll use the address of the interface
        # that is used to connect to the internet.
        public_ip = get_gateway_source_ip()
    if not mn_iface:
        # We are not connected to the network we have to manage. We don't know
        # what to do in this case so just tell that to the admin. We know this
        # handler will rerun when the config changes.
        hookenv.status_set(
            'blocked',
            'Cannot find interface that is connected to network {}.'.format(managed_network))
        return

    # Now that we know what interface we have to manage, let's check if there is
    # a dhcp server responding to requests from that interface. If there is no
    # dhcp server, we should install one.
    output = subprocess.check_output(['nmap', '--script', 'broadcast-dhcp-discover', '-S', mn_iface_ip], stderr=subprocess.STDOUT, universal_newlines=True)
    print(output)
    if 'DHCPOFFER' in output: # pylint: disable=E1135
        print('DHCP server found on this network. Will NOT create one.')
        remove_state('role.dhcp-server')
    else:
        print('No DHCP server found on this network, will create one.')
        set_state('role.dhcp-server')

    # Configure ourselves as a NAT gateway regardless of network topology so
    # port-forwarding always works.
    configure_nat_gateway(mn_iface, [public_if])

    # If our default gateway is not part of the managed network then we must
    # tell the clients on the managed network that we are their default gateway.
    # Otherwise, just pass our default gateway to the clients.
    gateway_if, gateway_ip = get_gateway()
    if gateway_if != mn_iface:
        print('Default gateway is NOT in the managed network so we tell potential clients we are their default gateway.')
        gateway_ip = mn_iface_ip
    else:
        print('Default gateway is on the managed network so we pass our default gateway to potential clients.')


    # Save these values so other handlers can use them.

    kv = unitdata.kv()
    kv.set('mn.iface', mn_iface)
    kv.set('mn.iface-ip', mn_iface_ip)
    kv.set('mn.gateway', gateway_ip)
    kv.set('public-ip', public_ip)   # PS: opened-ports uses this value too.
    set_state('gateway.installed')
    # Now we let the dhcp-server handlers know that they potentially have to
    # reconfigure their settings.
    remove_state('dhcp-server.configured')


@when('gateway.installed')
@when_not('role.dhcp-server')
def set_status():
    kv = unitdata.kv()
    public_ip = kv.get('public-ip')
    hookenv.status_set('active', 'Ready ({})'.format(public_ip))


################################################################################
#
#  DHCP SERVER FUNCTIONALITY
#
################################################################################

@when('role.dhcp-server')
@when_not('dhcp-server.installed')
def install():
    hookenv.log('Installing isc-dhcp')
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages(
        ['isc-dhcp-server']
    ))
    set_state('dhcp-server.installed')


@when_all('role.dhcp-server', 'dhcp-server.installed')
@when_not('dhcp-server.configured')
def configure_dhcp_server():
    kv = unitdata.kv()
    public_ip = kv.get('public-ip')
    mn_iface = kv.get('mn.iface')
    mn_gateway = kv.get('mn.gateway')
    managed_network = IPv4Network(config()["managed-network"])
    dhcp_range = config()["dhcp-range"]
    templating.render(
        source='isc-dhcp-server',
        target='/etc/default/isc-dhcp-server',
        context={
            'interfaces': mn_iface
        }
    )
    templating.render(
        source='dhcpd.conf',
        target='/etc/dhcp/dhcpd.conf',
        context={
            'subnet': str(managed_network.network_address),
            'netmask': str(managed_network.netmask),
            'routers': mn_gateway,                              # This is either the host itself or the host's gateway
            'broadcast_address': str(managed_network.broadcast_address),
            'domain_name_servers': ", ".join(get_dns()),        # We just copy the host's DNS settings
            'dhcp_range': dhcp_range,
        }
    )
    host.service_stop('isc-dhcp-server')
    success = host.service_start('isc-dhcp-server')
    if not success:
        message = "starting isc-dhcp-server failed. Please Check Charm configuration."
        if os.path.exists('/var/log/upstart/isc-dhcp-server.log'):
            with open('/var/log/upstart/isc-dhcp-server.log', 'r') as logfile:
                message += "Log: {}".format(logfile)
        hookenv.status_set('blocked', message)
        remove_state('dhcp-server.started')
        remove_state('dhcp-server.configured')
    else:
        hookenv.status_set('active', 'Ready ({})'.format(public_ip))
        set_state('dhcp-server.started')
        set_state('dhcp-server.configured')

################################################################################
#
#  NAT GATEWAY FUNCTIONALITY
#
################################################################################

@when_not('opened-ports.available')
@when('gateway.installed')
def forward_from_config():
    """Only forward ports from config if no opened-ports relation is available"""
    try:
        cfg = json.loads(config()["port-forwards"])
    except ValueError:
        hookenv.status_set(
            'blocked',
            'Failed to parse "port-forwards". Please make sure this is valid json.')
        exit()
    if not sanity_check_cfg(cfg):
        return
    update_port_forwards(cfg)


@when_all('opened-ports.available', 'gateway.installed')
def forward_from_config_and_relation(relation):
    """Forward ports from config and relations if opened-ports relation is available"""
    services = relation.opened_ports
    cfg = json.loads(config()["port-forwards"])
    if not sanity_check_cfg(cfg):
        return
    services.extend(cfg)
    update_port_forwards(services)
    services = relation.set_ready()


def sanity_check_cfg(cfg):
    for pf in cfg:
        if not 0 < int(pf['public_port']) <= 65535:
            hookenv.status_set(
                'blocked',
                'Requested public port {} is not between 0 and 65535.'.format(pf['public_port']))
            return False
        # Check if port is open.
        restricted_ports = subprocess.check_output(['ss -lntu | tr -s " " | cut -d " " -f 5 | rev | cut -d ":" -f 1 | rev | grep -E -o "[1-9][0-9]*" | sort -u'], shell=True, universal_newlines=True).split()
        if pf['public_port'] in restricted_ports:
            hookenv.status_set(
                'blocked',
                'Requested port-forward public port {} is already used by the OS. Used ports: ({})'.format(pf['public_port'], ", ".join(restricted_ports)))
            return False
    return True



################################################################################
#
#  HELPER FUNCTIONS
#
################################################################################

def get_dns():
    dns_ips = []
    with open('/etc/resolv.conf', 'r') as resolvfile:
        lines = resolvfile.readlines()
    for line in lines:
        columns = line.split()
        if columns[0] == 'nameserver':
            dns_ips.extend(columns[1:])
    return dns_ips


def get_routes():
    """ Returns the routes as an array with dicts for each route """
    output = subprocess.check_output(['route', '-n'], universal_newlines=True)
    output = output.split('\n', 1)[-1]
    soutput = output.split('\n', 1)
    [header, table] = soutput[0:2]
    coll_heads = header.lower().split()
    result = []
    for line in table.rstrip().split('\n'):
        coll_contents = line.split()
        r_dict = {}
        for i in range(0, len(coll_heads)):
            r_dict[coll_heads[i]] = coll_contents[i]
        result.append(r_dict)
    return result


def get_gateway():
    """ Returns tuple with (<interface to gateway>, <gateway ip>) """
    routes = get_routes()
    for route in routes:
        if route['destination'] == '0.0.0.0':
            return (route['iface'], route['gateway'])
