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
""" deploys a tengu model on a general ssh reachable cluster"""
import yaml


from config import  script_dir # pylint:disable=E0401

class ProviderException(Exception):
    pass


class JujuPoweredProvider(object):
    def __init__(self, global_conf):
        self.global_conf = global_conf

    def get(self, env_conf):
        return JujuPoweredEnv(self.global_conf, env_conf)

    def create_from_bundle(self, env_conf, bundle):
        env = self.get(env_conf)
        env.create(bundle)
        return env

    @property
    def userinfo(self):
        print("userinfo not implemented for ssh provider.")
        assert False

class JujuPoweredEnv(object):
    def __init__(self, global_conf, env_conf):
        self.global_conf = global_conf
        self.env_conf = env_conf
        self.files = {}

    def create(self, bundle): # pylint:disable=W0613,R0201
        print('Creating Juju powered environment...')
        with open("templates/env-configs.yaml", 'r') as configs_file:
            configs = yaml.load(configs_file.read())
        for key, value in configs.itervalues().next():
            self.env_conf['juju-env-conf'][key] = value
        self.env_conf['init-bundle'] = '{}/juju_powered_provider/templates/init-bundle/bundle.yaml'.format(script_dir)
        self.env_conf.save()

    def renew(self, hours): #pylint: disable=w0613,R0201
        print('Renew unnecessary in Juju powered environment...')

    def reload(self): # pylint:disable=W0613,R0201
        self.destroy()

    def destroy(self): # pylint:disable=W0613,R0201
        print('Destroying Juju powered environment')

    def expose(self, service): # pylint:disable=W0613,R0201
        print("expose not implemented for Juju powered environment. Cannot expose {}".format(service))
        assert False

    @property
    def machines(self):
        print("non-manual provider doesn't have machines")
        return []

    @property
    def status(self):
        return 'TODO Status'
