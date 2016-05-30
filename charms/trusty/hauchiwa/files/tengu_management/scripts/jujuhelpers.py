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
#pylint: disable=r0201,c0111,c0325,c0301
#
""" Handles communication to Juju """

from subprocess import check_output, STDOUT, CalledProcessError, Popen, PIPE
from subprocess import check_call
from time import sleep
import json
import sys
from base64 import b64encode, b64decode
import getpass
import tempfile
import os

# non standard pip dependencies
import yaml


USER = getpass.getuser()
HOME = '/home/{}'.format(USER)


class JujuException(Exception):
    pass

class JujuNotFoundException(JujuException):
    pass


class Service(object):
    def __init__(self, name, env):
        self.env = env
        self.name = name

    def upgrade(self):
        self.env.do('upgrade-charm', self.name)

    @property
    def exists(self):
        try:
            return self.status is not None
        except JujuNotFoundException:
            return False

    @property
    def status(self):
        """ Return status of service can be either None or following dict:
        {
            'service-status': '...',
            'message': '...',
        }"""
        info = self.env.status['services'].get(self.name)
        if not info:
            raise JujuNotFoundException('service {} not found'.format(self.name))
        return info

    @property
    def config(self):
        """ Return dictionary with configuration of deployed service"""
        output = self.env.do('get', self.name, format='yaml')
        return yaml.load(output)

    def set_config(self, config):
        """ Update config of service to values in given dictionary. Format of dictionary:
        {
            '<config-key>': '....',
        }

        Please note that this format is different from what you get when asking the config of a service."""
        config = {self.name: config}
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                # do stuff with temp file
                tmp.write(yaml.dump(config))
            self.env.do('set', self.name, config=tmp.name)
        finally:
            os.remove(tmp.name)

    def wait_until(self, requested_status):
        """ Wait until service contains status in its message """
        sys.stdout.write('waiting until {} service is {} '.format(self.name, requested_status))
        while(True):
            current_status = self.status
            if (current_status['service-status']['current'] and current_status['service-status'].get('message') and (requested_status.lower() in current_status['service-status'].get('message').lower())):
                break
            sleep(5)
            sys.stdout.write('.')
            sys.stdout.flush()
        sys.stdout.write('{} is {}!\n'.format(self.name, requested_status))


class JujuEnvironment(object):
    """ handles an existing Juju environment """
    def __init__(self, _name=None):
        if _name:
            self.name = _name
        else:
            self.name = self.current_env()


    def do(self, action, *args, **kwargs): #pylint: disable=c0103
        args += ('-e', self.name)
        return JujuEnvironment.juju_do(action, *args, **kwargs)


    @staticmethod
    def juju_do(action, *args, **kwargs):
        command = ['juju', action]
        # Add all the arguments to the command
        command.extend(args)
        # Ad all the keyword arguments to the command
        for key, value in kwargs.iteritems():
            command.extend(['--{}'.format(key), value])
        # convert all elements in command to string
        command = [str(i) for i in command]
        try:
            output = check_output_error(command)
            return output
        except CalledProcessError as ex:
            if 'missing namespace, config not prepared' in ex.output:
                raise JujuNotFoundException("missing namespace, config not prepared")
            if "ERROR Unable to connect to environment" in ex.output:
                raise JujuNotFoundException("ERROR Unable to connect to environment")
            raise JujuException(ex.output)


    @property
    def machines(self):
        """ Return machines"""
        return self.status['machines'].keys()


    @property
    def services(self):
        """ Returns services"""
        return self.status['services'].keys()


    @property
    def status(self):
        """ Return dictionary with output of juju status """
        output = self.do('status', format='json')
        return json.loads(output)


    def get_services(self, startstring, key, value):
        services = []
        status = self.status
        for service_name in status['services'].keys():
            if service_name.startswith(startstring):
                config = Service(service_name, self).config
                if config['settings'][key]['value'] == value:
                    services.append({service_name:  status['services'][service_name]})
        return services


    @property
    def password(self):
        """ Gets the default password from the Juju environment"""
        file_path = '{}/.juju/environments/{}.jenv'.format(HOME, self.name)
        stream = open(file_path, "r")
        doc = yaml.load(stream)
        password = doc.get('password')
        return password


    @property
    def bootstrap_user(self):
        """ Gets the bootstrap user from the Juju environment"""
        file_path = '{}/.juju/environments/{}.jenv'.format(HOME, self.name)
        stream = open(file_path, "r")
        doc = yaml.load(stream)
        password = doc.get('bootstrap-config').get('bootstrap-user')
        return password


    def add_machines(self, machines):
        """ Add all machines received from provider to Juju environment"""
        print "adding machines to juju"
        processes = set()
        for machinefqdn in machines:
            print '\tAdding %s' % machinefqdn
            processes.add(Popen([
                'juju', 'add-machine',
                'ssh:{}@{}'.format(self.bootstrap_user, machinefqdn)
            ]))
            sleep(10)
        for proc in processes:
            if proc.poll() is None:
                proc.wait()
            if proc.poll() > 0:
                raise JujuException('error while adding machines')


    def deploy(self, charm, name, **options):
        """ Deploy <charm> as <name> with config in <config_path> """
        self.do('deploy', charm, name, **options)
        return Service(name, self)


    def add_unit(self, name, **options):
        """ Add unit to existing Charm"""
        self.do('add-unit', name, **options)


    def deploy_bundle(self, bundle_path, *args, **options):
        """ Deploy Juju bundle """
        return self.do('deployer', '-c', bundle_path, *args, **options)


    def action_do(self, unit, action, **options):
        return self.do('action do', unit, action, **options)


    def destroy_service(self, name):
        """ Deploy <charm> as <name> with config in <config_path> """
        c_action = ['juju', 'destroy']
        c_charm = [name]
        c_force = ['--force']
        command = c_action + c_charm + c_force
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            raise JujuException(ex.output)


    def add_relation(self, charm1, charm2):
        """ add relation between two charms """
        self.do('add-relation', charm1, charm2)


    def return_environment(self):
        """ returns exported juju environment"""
        env_conf = {'environment-name': str(self.name)}
        with open('{}/.juju/environments.yaml'.format(HOME), 'r') as e_file:
            e_content = yaml.load(e_file)
        env_conf['environment-config'] = b64encode(
            yaml.dump(
                e_content['environments'][self.name],
                default_flow_style=False
            )
        )
        with open('{}/.juju/environments/{}.jenv'.format(HOME, self.name),
                  'r') as e_file:
            e_content = e_file.read()
        env_conf['environment-jenv'] = b64encode(e_content)
        # We don't need to export ssh keys since juju can just add the current ones.
        # with open('{}/.juju/ssh/juju_id_rsa'.format(HOME), 'r') as e_file:
        #     e_content = e_file.read()
        # env_conf['environment-privkey'] = b64encode(e_content)
        # with open('{}/.juju/ssh/juju_id_rsa.pub'.format(HOME), 'r') as e_file:
        #     e_content = e_file.read()
        # env_conf['environment-pubkey'] = b64encode(e_content)
        return env_conf


    @staticmethod
    def switch_env(name):
        """switch active juju environment to self"""
        JujuEnvironment.juju_do('switch', name)


    @staticmethod
    def list_environments():
        """Checks if Juju env with given name exists."""
        return JujuEnvironment.juju_do('switch', '--list').split()


    @staticmethod
    def env_exists(name):
        """Checks if Juju env with given name exists."""
        envs = JujuEnvironment.list_environments()
        return name in envs


    @staticmethod
    def current_env():
        """ Returns the current active Juju environment """
        return JujuEnvironment.juju_do('switch').rstrip()


    @staticmethod
    def create(name, bootstrap_host, juju_config, machines):
        """Creates Juju environment, add all available machines,
        deploy juju_gui"""
        JujuEnvironment._create_env(name, bootstrap_host, juju_config)
        # Wait 5 seconds before adding machines because python
        # is too fast for juju
        sleep(20)
        environment = JujuEnvironment(name)
        environment.add_machines(machines)
        environment.deploy_lxc_networking()
        print("deploying openvpn")
        environment.deploy('local:openvpn', 'openvpn', to='0')
        print("Creation of bare Tengu complete!")
        return environment


    def deploy_lxc_networking(self):
        lxc_networking = self.deploy("local:lxc-networking", "lxc-networking", to='0')
        for machine in self.machines:
            if machine != '0':
                self.add_unit('lxc-networking', to=machine)
        lxc_networking.wait_until('Ready')
        dhcp_server = self.deploy("local:dhcp-server", "dhcp-server", to='0')
        dhcp_server.wait_until('Ready')


    @staticmethod
    def _create_env(name, bootstrap_host, juju_config):
        """ Add new Juju environment with name = name
        and bootstrap this environment """
        print "adding juju environment %s" % name
        name = str(name)
        juju_config['bootstrap-host'] = bootstrap_host
        # get original environments config
        with open("{}/.juju/environments.yaml".format(HOME), 'r') as config_file:
            config = yaml.load(config_file)
        if config['environments'] is None:
            config['environments'] = dict()
        # add new environment
        config['environments'][name] = juju_config
        # write new environments config
        with open("{}/.juju/environments.yaml".format(HOME), 'w') as config_file:
            config_file.write(yaml.dump(config, default_flow_style=False))
        # Bootstrap new environmnent
        try:
            check_output(['juju', 'switch', name], stderr=STDOUT)
            print "bootstrapping juju environment"
            sleep(5) # otherwise we get a weird error
            check_call(['juju', 'bootstrap'])
        except CalledProcessError as ex:
            raise JujuException(ex.output)


    @staticmethod
    def import_environment(env_conf):
        name = env_conf['environment-name']
        conf = yaml.load(b64decode(env_conf['environment-config']))
        jenv = b64decode(env_conf['environment-jenv'])
        pubkey = b64decode(env_conf['environment-pubkey'])
        privkey = b64decode(env_conf['environment-privkey'])
        with open('{}/.juju/environments.yaml'.format(HOME), 'r') as e_file:
            e_content = yaml.load(e_file)
        with open('{}/.juju/environments.yaml'.format(HOME), 'w+') as e_file:
            e_content['environments'][name] = conf
            e_file.write(yaml.dump(e_content, default_flow_style=False))
        with open('{}/.juju/environments/{}.jenv'.format(HOME, name), 'w+') as e_file:
            e_file.write(jenv)
        with open('{}/.juju/ssh/juju_id_rsa'.format(HOME), 'w+') as e_file:
            e_file.write(privkey)
        with open('{}/.juju/ssh/juju_id_rsa.pub'.format(HOME), 'w+') as e_file:
            e_file.write(pubkey)
        JujuEnvironment.switch_env(name)


def check_output_error(*popenargs, **kwargs):
    process = Popen(stdout=PIPE, stderr=PIPE, *popenargs, **kwargs)
    output, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd, output=stderr)
    return output
