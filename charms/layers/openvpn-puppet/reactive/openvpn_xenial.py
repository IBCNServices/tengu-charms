#!/usr/bin/env python3
#pylint: disable=c0111
import os
import stat
import errno
import shutil
from ipaddress import IPv4Address

from charms.reactive import when_all
from charms.layer.puppet_base import Puppet
from charmhelpers.core import templating
from charmhelpers.core.hookenv import config, status_set

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
        'servername' : SERVERNAME,
        'country' : conf['key-country'],
        'province' : conf['key-province'],
        'city' : conf['key-city'],
        'organization' : conf['key-org'],
        'email' : conf['key-email'],
        'protocol' : conf['protocol'],
        'port' : conf['port'],
        'duplicate_cn' : conf['duplicate-cn'],
        'push_dns' : conf['push-dns'],
        'dns_server' : dns_info.get('server', "8.8.8.8"),
        'dns_search_domain' : dns_info.get('domain', ""),
        'clients' : clients,
        'ext_ip' : get_most_public_ip(),
    }
    templating.render(
        source='init.pp',
        target='/opt/openvpn-puppet/init.pp',
        context=context
    )
    puppet.apply('/opt/openvpn-puppet/init.pp')
    copy_client_configs_to_home(clients)
    status_set('active', 'Ready')


def copy_client_configs_to_home(clients):
    for client in clients:
        source = "/etc/openvpn/{}/download-configs/{}.ovpn".format(SERVERNAME,
                                                                   client)
        dest = "/home/ubuntu/{}.ovpn".format(client)
        shutil.copy(source, dest)
        shutil.chown(dest, user="ubuntu", group="ubuntu")
        os.chmod(dest,
                 stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR)


def get_most_public_ip():
    '''returns public ip. If no ip of server is public, it returns ip from
    `facter`
    '''
    facter = Puppet().facter()
    ext_ip = None
    for key in facter.keys():
        if key.startswith('ipaddress'):
            address = IPv4Address(facter[key])
            # Can't use is_global in 14.04 because of: https://bugs.python.org/issue21386
            if not address.is_private:
                ext_ip = address
                break
    if not ext_ip:
        ext_ip = facter['ipaddress']
    return ext_ip


def get_dns_info():
    info = {}
    with open('/etc/resolv.conf', 'r') as resolv_file:
        content = resolv_file.readlines()
    for line in content:
        words = line.split()
        if words[0] == "nameserver":
            info['nameserver'] = words[1]
        elif words[0] == "search":
            info['search'] = words[1]
    return info
