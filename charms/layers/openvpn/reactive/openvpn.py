#!/usr/bin/env python3
# pylint: disable=c0111
import os
import stat
import errno
import shutil
from ipaddress import IPv4Address

from charms.reactive import when_all
from charms.layer.puppet_base import Puppet
from charmhelpers.core import templating, unitdata
from charmhelpers.core.hookenv import (
    config,
    status_set,
    open_port,
    close_port
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
        'ext_ip': get_extip_and_networks()['external-ip'],
        'internal_networks': get_extip_and_networks()['internal-networks'],
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
        ext_ip = facter['ipaddress']
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
