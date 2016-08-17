#!/usr/bin/python
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
# pylint: disable=C0111,c0321,c0301,c0325
#
""" deploys a tengu model """
from time import sleep
from os.path import expanduser
import sys
import json
import subprocess

# non-default pip dependencies
import click
import yaml

# Own modules
from rest2jfed_connector import Rest2jfedConnector
import jujuhelpers # pylint: disable=E0401
import rspec_utils
from output import fail # pylint: disable=E0401

TENGU_DIR = expanduser("~/.tengu")

class ProviderException(click.ClickException):
    pass


class JfedProvider(object):
    def __init__(self, global_conf):
        self.global_conf = global_conf

    def get(self, env_conf):
        return JfedSlice(self.global_conf, env_conf)

    def create_from_bundle(self, env_conf, bundle):
        env = self.get(env_conf)
        env.generate_rspec(bundle)
        env.create()
        return env

    @property
    def userinfo(self):
        jfed = self.init_bare_jfed()
        return jfed.get_userinfo()

    def init_bare_jfed(self):
        return Rest2jfedConnector(self.global_conf['rest2jfed-hostname'],
                                  self.global_conf['rest2jfed-port'],
                                  self.global_conf['s4-cert-path'],
                                  self.global_conf['project-name'],
                                  None,
                                  locked=True)


class JfedSlice(object):
    def __init__(self, global_conf, env_conf):
        self.rspec_path = "{}/juju-tengu.rspec".format(env_conf.dir)
        self.manifest_path = "{}/manifest.mrspec".format(env_conf.dir)

        self.global_conf = global_conf
        self.env_conf = env_conf

        self.name = self.env_conf['env-name']
        self.locked = env_conf['locked']
        self.bootstrap_user = env_conf['juju-env-conf']['bootstrap-user']

        self.files = {
            "rspec" : self.rspec_path,
            "manifest" : self.manifest_path,
            "emulab-s4-cert" : self.global_conf['s4-cert-path'],
        }

    def create(self):
        print('Creating jfed slice and slivers, this might take a while...')
        jfed = self.init_jfed()
        jfed.create(self.rspec_path, self.manifest_path)
        self.env_conf['juju-env-conf']['bootstrap-host'] = self.get_machines(include_bootstrap_host=True).pop(0)
        self.env_conf.save()
        self.wait_for_init()


    def renew(self, hours):
        print('Renewing jfed slice and slivers...')
        jfed = self.init_jfed()
        jfed.renew(hours)
        print('renewed slice and slivers succesfully')


    def reload(self):
        if self.locked:
            fail('Cannot reload locked model')
        else:
            print('Reloading jfed slivers...')
            jfed = self.init_jfed()
            jfed.reload()
            print('renewed reloaded succesfully')


    def destroy(self):
        if self.locked:
            fail('Cannot destroy locked model')
        else:
            print('Destroying jfed slice and slivers...')
            jfed = self.init_jfed()
            jfed.delete()


    def expose(self, service):
        next_pub_port = 30000
        dhcp_server = jujuhelpers.Service('network-agent', service.env)
        forward_config = json.loads(dhcp_server.config['settings']['port-forwards']['value'])
        next_pub_port = int(dhcp_server.config['settings']['portrange']['value']) + 1000
        if next_pub_port <= max([int(pf['public_port']) for pf in forward_config] or [0]):
            next_pub_port = max([int(pf['public_port']) for pf in forward_config] or [0]) + 1
        pf_curlist = set([(pf['private_ip'], pf['private_port'], pf['protocol']) for pf in forward_config])
        pf_nelist = set()
        for (unitinfo) in service.status['units'].values():
            for port, protocol in [op.split('/') for op in unitinfo.get('open-ports')]:
                pf_nelist.add((unitinfo['public-address'], port, protocol))
        pf_addlist = pf_nelist - pf_curlist
        for private_ip, private_port, protocol in pf_addlist:
            forward_config.append({
                'private_ip': private_ip,
                'private_port': private_port,
                'protocol': protocol,
                'public_port': next_pub_port,
            })
            next_pub_port += 1
        dhcp_server.set_config({'port-forwards': json.dumps(forward_config, indent=4)})
        print(show_pf_result(forward_config, pf_nelist, dhcp_server.status['units'].itervalues().next()['workload-status']['message'].lstrip('Ready (').rstrip(')')))


    def wait_for_init(self):
        """Waits until the init script has run"""
        bootstrap_host = self.env_conf['juju-env-conf']['bootstrap-host']
        bootstrap_user = self.env_conf['juju-env-conf']['bootstrap-user']
        print('Waiting for {} to finish partition resize'.format(bootstrap_host))
        output = None
        while True:
            sys.stdout.write('.')
            sys.stdout.flush()
            try:
                output = subprocess.check_output([
                    'ssh',
                    '-o',
                    'StrictHostKeyChecking=no',
                    '{}@{}'.format(bootstrap_user, bootstrap_host),
                    '[[ -f /var/log/tengu-init-done ]] && echo "1"'
                ])
            except subprocess.CalledProcessError:
                pass
            if output and output.rstrip() == '1':
                break
            sleep(5)
        sys.stdout.write('\n')

    def get_machines(self, include_bootstrap_host=False):
        try:
            if include_bootstrap_host:
                return rspec_utils.get_machines(self.manifest_path)
            else:
                return rspec_utils.get_machines(self.manifest_path)[1:]
        except IOError:
            raise ProviderException('Manifest not found')

    @property
    def machines(self):
        return self.get_machines()


    @property
    def status(self):
        jfed = self.init_jfed()
        return jfed.get_full_status()


    def init_jfed(self):
        return Rest2jfedConnector(self.global_conf['rest2jfed-hostname'],
                                  self.global_conf['rest2jfed-port'],
                                  self.global_conf['s4-cert-path'],
                                  self.global_conf['project-name'],
                                  self.name,
                                  locked=self.locked)


    def generate_rspec(self, bundle):
        data = get_data_from_bundle(bundle)
        nrnodes = data['nrnodes']
        pub_ipv4 = data['pub_ipv4']
        testbed = data['testbed']
        userkeys = [{
            'user' : self.bootstrap_user,
            'pubkey' : self.global_conf['pubkey'],
        }]
        rspec = rspec_utils.create_rspec(nrnodes, userkeys, pub_ipv4, testbed)
        with open(self.rspec_path, 'w+') as rspec_file:
            rspec_file.write(rspec)


def count_machines(bundle_path):
    try:
        with open(bundle_path, 'r') as bundle_file:
            bundle = yaml.load(bundle_file)
    except yaml.YAMLError as yamlerror:
        raise click.ClickException('Parsing bundle \033[91mfailed\033[0m: {}'.format(str(yamlerror)))
    return len(bundle['machines'])


def get_data_from_bundle(bundle):
    machines = bundle.get('machines')
    if not machines: raise ProviderException('Parsing bundle \033[91mfailed\033[0m: Could not find "machines" item in bundle.')
    if not len(machines) > 0: raise ProviderException('Parsing bundle \033[91mfailed\033[0m: There has to be at least 1 machine specified')
    testbed = None
    pub_ipv4 = False
    for m_id in range(len(machines)):
        if not machines.get(str(m_id)): raise ProviderException('Parsing bundle \033[91mfailed\033[0m: machine {} not found while number of machines is {}.'.format(m_id, len(machines)))
        if m_id == 0:
            annotations = machines[str(m_id)].get('annotations', dict())
            testbed = annotations.pop('testbed', 'wall1')
            pub_ipv4 = annotations.pop('pubipv4', False)
            for annotation in annotations:
                print('WARNING: annotation {} unknown'.format(annotation))
    return {
        'nrnodes' : len(machines),
        'testbed' : testbed,
        'pub_ipv4' : pub_ipv4,
    }


def show_pf_result(forward_config, pf_nelist, public_ip):
    output = ''
    for port_forward in forward_config:
        if (port_forward['private_ip'], port_forward['private_port'], port_forward['protocol']) in pf_nelist:
            output += '{}:{} is accessible at {}:{}\n'.format(port_forward['private_ip'], port_forward['private_port'], public_ip, port_forward['public_port'])
    return output
