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
""" deploys a tengu env """
from os.path import expanduser

# non-default pip dependencies
import click
import yaml

# Own modules
from rest2jfed_connector import Rest2jfedConnector
import rspec_utils

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


    def renew(self, hours):
        print('Renewing jfed slice and slivers...')
        jfed = self.init_jfed()
        jfed.renew(hours)
        print('renewed slice and slivers succesfully')


    def reload(self):
        print('Reloading jfed slivers...')
        jfed = self.init_jfed()
        jfed.reload()
        print('renewed reloaded succesfully')


    def destroy(self):
        print('Destroying jfed slice and slivers...')
        jfed = self.init_jfed()
        jfed.delete()


    @property
    def machines(self):
        try:
            return rspec_utils.get_machines(self.manifest_path)
        except IOError:
            raise ProviderException('Manifest not found')

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
            constraints = machines[str(m_id)].get('constraints').split()
            for constraint in constraints:
                try:
                    key, value = constraint.split('=', 1)
                except ValueError as valueerr:
                    print('cannot decode constraint: {}'.format(constraint))
                    print(valueerr.message)
                    continue
                if key == 'testbed':
                    testbed = value
                elif key == 'pubipv4' and value.lower() == 'true':
                    pub_ipv4 = True
                elif key not in ['arch']:
                    print('WARNING: constraint {} unknown'.format(constraint))
            if not testbed: raise ProviderException("Parsing bundle \033[91mfailed\033[0m: machine {} doesn't specify testbed.".format(m_id))
    return {
        'nrnodes' : len(machines),
        'testbed' : testbed,
        'pub_ipv4' : pub_ipv4,
    }


# env = provider.get(env_conf)
# env.create_from_bundle
# env.delete()
# env.status()
# env.renew()
