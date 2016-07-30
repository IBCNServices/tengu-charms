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
""" deploys a tengu env on a general ssh reachable cluster"""
import subprocess

import click
import yaml

from config import script_dir # pylint: disable=E0401


class ProviderException(Exception):
    pass


class SSHProvider(object):
    def __init__(self, global_conf):
        self.global_conf = global_conf

    def get(self, env_conf):
        return SSHEnv(self.global_conf, env_conf)

    def create_from_bundle(self, env_conf, bundle):
        env = self.get(env_conf)
        env.create(bundle)
        return env

    @property
    def userinfo(self):
        print("userinfo not implemented for ssh provider.")
        assert False

class SSHEnv(object):
    def __init__(self, global_conf, env_conf):
        self.bundle_path = "{}/bundle.yaml".format(env_conf.dir)

        self.global_conf = global_conf
        self.env_conf = env_conf

        self.files = {
            "bundle": self.bundle_path
        }

    def create(self, bundle):
        print('Creating Tengu SSH environment...')
        bootstrap_user = self.env_conf['juju-env-conf']['bootstrap-user']
        with open("{}/bundle.yaml".format(self.env_conf.dir), 'w') as outfile:
            outfile.write(yaml.dump(bundle, default_flow_style=True))
        machine_list = self.machines
        for machine in machine_list:
            subprocess.call(["scp", '-o', 'StrictHostKeyChecking=no', "%s/ssh_provider/ssh_prepare.sh" % script_dir(),
                             '{}@{}:~/ssh_prepare.sh'.format(bootstrap_user, machine)])
            subprocess.call(
                ["ssh", '-o', 'StrictHostKeyChecking=no', '{}@{}'.format(bootstrap_user, machine), "~/ssh_prepare.sh"])

    def renew(self, hours): #pylint: disable=w0613,R0201
        print('Renew unnecessary in SSH environment...')

    def reload(self):
        self.destroy()

    def destroy(self):
        bootstrap_user = self.env_conf['juju-env-conf']['bootstrap-user']
        print('Removing Juju environment from nodes...')
        machine_list = self.machines
        if click.confirm('Warning! I will ssh to [{}] and start deleting very important files. Are you sure you want to continue?'.format(machine_list)):
            for machine in machine_list:
                subprocess.call(["scp", '-o', 'StrictHostKeyChecking=no', "%s/ssh_provider/ssh_destroy.sh" % script_dir(),
                                 '{}@{}:~/ssh_destroy.sh'.format(bootstrap_user, machine)])
                subprocess.call(
                    ["ssh", '-o', 'StrictHostKeyChecking=no', '{}@{}'.format(bootstrap_user, machine), "~/ssh_destroy.sh"])

    def expose(self, service):
        print("expose not implemented for ssh provider. Cannot expose {}".format(service))
        assert False

    @property
    def machines(self):
        try:
            with open(self.bundle_path, 'r') as bundle_file:
                bundle = yaml.load(bundle_file)
            return get_machines_from_bundle(bundle)
        except IOError:
            raise ProviderException('Bundle not found')

    @property
    def status(self):
        machine_list = self.machines
        for machine in machine_list:
            print(machine)
        return 'TODO Status'


def get_machines_from_bundle(bundle):
    machines = bundle.get('machines')
    machines_list = list()
    if not machines: raise Exception('Could not find machines item in bundle.')
    if not len(machines) > 0: raise Exception('There has to be at least 1 machine specified')
    for m_id in range(len(machines)):
        if not machines.get(str(m_id)): raise Exception(
            'machine {} not found while number of machines is {}.'.format(m_id, len(machines)))
        constraints = machines[str(m_id)].get('constraints').split()
        for constraint in constraints:
            if constraint.startswith('host='):
                machines_list.append(constraint.split('=')[1])
    return machines_list
