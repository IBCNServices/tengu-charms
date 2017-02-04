#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
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
import os
import stat
import errno
import shutil
from ipaddress import IPv4Address

from charms.reactive import when_all
from charms.layer.puppet_base import Puppet  # pylint: disable=E0611,E0401
from charmhelpers.core import templating, unitdata
from charmhelpers.core.hookenv import (
    config,
    status_set,
    open_port,
    close_port,
    unit_get,
)

SERVERNAME = "openvpn-server1"


@when_all('puppet.standalone.installed', 'config.changed')
def install_openvpn_xenial():
    puppet = Puppet()
    try:
        os.makedirs('/opt/openvpn-puppet')
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    conf = config()
    dns_info = get_dns_info()
    clients = conf['clients'].split()
    eipndict = get_extip_and_networks()
    ext_ip = eipndict['external-ip']
    pub_ip = eipndict['external-ip']
    # If public-address is different from private-address, we're probably in a
    # juju-supported cloud that we can trust to give us the right address that
    # clients need to use to connect to us.
    if unit_get('private-address') != unit_get('public-address'):
        pub_ip = unit_get('public-address')
    internal_networks = eipndict['internal-networks']
    context = {
        'servername': SERVERNAME,
        'country': conf['key-country'],
        'province': conf['key-province'],
        'city': conf['key-city'],
        'organization': conf['key-org'],
        'email': conf['key-email'],
        'protocol': conf['protocol'],
        'port': conf['port'],
        'duplicate_cn': conf['duplicate-cn'],
        'push_dns': conf['push-dns'],
        'push_default_gateway': conf['push-default-gateway'],
        'dns_server': dns_info.get('nameserver', "8.8.8.8"),
        'dns_search_domains': dns_info.get('search', []),
        'clients': clients,
        'ext_ip': ext_ip,
        'pub_ip': pub_ip,
        'internal_networks': internal_networks,
    }
    templating.render(
        source='init.pp',
        target='/opt/openvpn-puppet/init.pp',
        context=context
    )
    kv_store = unitdata.kv()
    if kv_store.get('previous-port') and kv_store.get('previous-protocol'):
        close_port(kv_store.get('previous-port'),
                   protocol=kv_store.get('previous-protocol'))
    puppet.apply('/opt/openvpn-puppet/init.pp')
    copy_client_configs_to_home(clients)
    status_set('active', 'Ready')
    open_port(conf['port'], protocol=conf['protocol'].upper())
    kv_store.set('previous-port', conf['port'])
    kv_store.set('previous-protocol', conf['protocol'].upper())


def copy_client_configs_to_home(clients):
    for client in clients:
        source = "/etc/openvpn/{}/download-configs/{}.ovpn".format(SERVERNAME,
                                                                   client)
        dest = "/home/ubuntu/{}.ovpn".format(client)
        shutil.copy(source, dest)
        shutil.chown(dest, user="ubuntu", group="ubuntu")
        os.chmod(dest,
                 stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR)


def get_extip_and_networks():
    '''returns public ip. If no ip of server is public, it returns ip from
    `facter`
    '''
    facter = Puppet().facter('networking')
    ext_ip = None
    internal_networks = []
    for iface, content in facter['networking']['interfaces'].items():
        if not any(bl_iface in iface for bl_iface in ['lo', 'tun']):
            for binding in content.get('bindings', []):
                address = IPv4Address(binding['address'])
                #
                # GET PUBLIC IP
                # Can't use is_global in 14.04 because of following bug:
                # https://bugs.python.org/issue21386
                if not address.is_private:
                    ext_ip = address
                #
                # GET PRIVATE IPS
                #
                else:
                    internal_networks.append(
                        "{} {}".format(binding['network'], binding['netmask']))
    if not ext_ip:
        ext_ip = facter['networking']['ip']
    return {
        "external-ip": ext_ip,
        "internal-networks": internal_networks,
    }


def get_dns_info():
    info = {}
    with open('/etc/resolv.conf', 'r') as resolv_file:
        content = resolv_file.readlines()
    for line in content:
        words = line.split()
        if words[0] == "nameserver":
            info['nameserver'] = words[1]
        elif words[0] == "search":
            info['search'] = words[1:]
    return info
