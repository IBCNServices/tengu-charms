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
# pylint: disable=c0111,c0103,c0301
import os
import json
import socket
import subprocess

from charmhelpers.core import hookenv, templating, host
from charmhelpers.core.hookenv import config
from charmhelpers import fetch
from charms.reactive import hook, when, when_not, when_all, set_state, when_any, remove_state
#from charms.reactive.helpers import data_changed

# modules from Pip dependencies
from netifaces import AF_INET
import netifaces
import netaddr

# Own modules
from iptables import update_port_forwards, configure_nat_gateway, remove_nat_gateway_config

# Forward ports from config and relations
@when_all('opened-ports.available', 'dhcp-server.installed')
def configure_port_forwards(relation):
    services = relation.opened_ports
    cfg = json.loads(config()["port-forwards"])
    # sanity check config
    for pf in cfg:
        if not 0 < int(pf['public_port']) <= 65535:
            hookenv.status_set(
                'blocked',
                'Requested public port {} is not between 0 and 65535.'.format(pf['public_port']))
            return
        # Check if port is open.
        restricted_ports = subprocess.check_output(['ss -lntu | tr -s " " | cut -d " " -f 5 | rev | cut -d ":" -f 1 | rev | grep -E -o "[1-9][0-9]*" | sort -u'], shell=True, universal_newlines=True).split()
        if pf['public_port'] in restricted_ports:
            hookenv.status_set(
                'blocked',
                'Requested port-forward public port {} is already used by the OS. Used ports: ({})'.format(pf['public_port'], ", ".join(restricted_ports)))
            return
    services.extend(cfg)
    update_port_forwards(services)
    services = relation.set_ready()


# Only forward ports from config
@when_not('opened-ports.available')
@when('dhcp-server.installed')
def configure_forwarders():
    cfg = json.loads(config()["port-forwards"])
    update_port_forwards(cfg)


@hook('upgrade-charm')
def upgrade_charm():
    install()
    configure()


@when_not('dhcp-server.installed')
def install():
    hookenv.log('Installing isc-dhcp')
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages(
        ['isc-dhcp-server', 'iptables-persistent']
    ))
    set_state('dhcp-server.installed')


@when_any(
    'config.changed.dhcp-network',
    'config.changed.dhcp-range',
    'config.changed.dhcp-network'
)
@when('dhcp-server.installed')
def configure():
    hookenv.log('Configuring isc-dhcp')
    dhcp_network = netaddr.IPNetwork(config()["dhcp-network"])
    dhcp_range = config()["dhcp-range"]
    dns = ", ".join(get_dns())
    dhcp_if = None
    public_ifs = []
    dhcp_netmask = None
    dhcp_addr = None
    for interface in netifaces.interfaces():
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet and af_inet[0].get('broadcast'):
            broadcast = netifaces.ifaddresses(interface)[AF_INET][0]['broadcast']
            netmask = netifaces.ifaddresses(interface)[AF_INET][0]['netmask']
            addr = netifaces.ifaddresses(interface)[AF_INET][0]['addr']
            if netaddr.IPAddress(addr) in dhcp_network:
                dhcp_if = interface
                dhcp_addr = addr
                dhcp_netmask = netmask
                dhcp_broadcast = broadcast
            else:
                public_ifs.append(interface)
    if not dhcp_if:
        hookenv.status_set(
            'blocked',
            'Cannot find interface that is connected to network {}.'.format(dhcp_network))
        return
    # If we are serving dhcp on a different network than the default gateway;
    # then configure the host as NATted gateway. Else, use host's gateway for dhcp clients.
    gateway_if, gateway_ip = get_gateway()
    if gateway_if != dhcp_if:
        print('Default gateway is NOT on dhcp network, configuring host as gateway.')
        gateway_ip = dhcp_addr
        configure_nat_gateway(dhcp_if, public_ifs)
    else:
        print('Default gateway is on dhcp network')
        remove_nat_gateway_config()
    templating.render(
        source='isc-dhcp-server',
        target='/etc/default/isc-dhcp-server',
        context={
            'interfaces': dhcp_if
        }
    )
    templating.render(
        source='dhcpd.conf',
        target='/etc/dhcp/dhcpd.conf',
        context={
            'subnet': dhcp_network.ip,
            'netmask': dhcp_netmask,
            'routers': gateway_ip,                  # This is either the host itself or the host's gateway
            'broadcast_address': dhcp_broadcast,
            'domain_name_servers': dns,             # We just use the host's DNS settings
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
    else:
        hookenv.status_set('active', 'Ready ({})'.format(get_pub_ip()))
        set_state('dhcp-server.started')


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


def get_pub_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("google.com", 80))
    public_address = sock.getsockname()[0]
    sock.close()
    return public_address
