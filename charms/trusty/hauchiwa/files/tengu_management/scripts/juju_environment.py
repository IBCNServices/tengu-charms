# import pprint
# pprint.pprint(config)
#
#
""" Handles communication to Juju """

from os.path import expanduser
from subprocess import check_output, STDOUT, CalledProcessError, PIPE, Popen
from time import sleep
import yaml
import json

class JujuEnvironment(object):
    """ handles an existing Juju environment """
    def __init__(self, _name):
        self.name = _name
        JujuEnvironment.switch_env(self.name)


    def get_machine_id(self, fqdn): # pylint: disable=R0201
        """ gets machine id from machine fqdn """
        import re
        machine_regex = re.compile('^ +"([0-9]+)":$')
        dns_regex = re.compile('^ +dns-name: +' + fqdn + '$')
        cmd = Popen('juju status', shell=True, stdout=PIPE)
        for line in cmd.stdout:
            mid = machine_regex.match(line)
            dns = dns_regex.match(line)
            if mid != None:
                current_machine = mid.group(1)
            elif dns != None:
                return current_machine
        print "machine not found"


    @property
    def machines(self):
        """ Return machines"""
        return self.status['machines'].keys()


    @property
    def services(self):
        """ Returns services"""
        return self.status['services'].keys()


    @property
    def status(self): # pylint: disable=R0201
        """ Return dictionary with output of juju status """
        try:
            output = check_output(["juju", "status", "--format=json"],
                                  stderr=STDOUT)
            return json.loads(output)
        except CalledProcessError as ex:
            print ex.output
            raise

    @property
    def juju_password(self):
        """ Gets the default password from the Juju environment"""
        file_path = expanduser('~/.juju/environments/%s.jenv' % self.name)
        stream = open(file_path, "r")
        doc = yaml.load(stream)
        password = doc.get('password')
        return password

    @property
    def bootstrap_user(self):
        """ Gets the bootstrap user from the Juju environment"""
        file_path = expanduser('~/.juju/environments/%s.jenv' % self.name)
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
        for proc in processes:
            if proc.poll() is None:
                proc.wait()
            if proc.poll() > 0:
                raise Exception('error while adding machines')


    def deploy_gui(self): # pylint: disable=R0201
        """ Deploys juju-gui to node 0 """
        try:
            # TODO: We don't need to wait for this to finish
            check_output(['juju', 'deploy', 'juju-gui', '--to', '0'],
                         stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise

    @staticmethod
    def switch_env(name):
        """switch to environment with given name"""
        try:
            check_output(['juju', 'switch', name], stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise

    @staticmethod
    def env_exists(name):
        """Checks if Juju env with given name exists."""
        try:
            envs = check_output(['juju', 'switch', '--list'],
                                stderr=STDOUT).split()
        except CalledProcessError as ex:
            print ex.output
            raise
        return name in envs

    @staticmethod
    def current_env():
        """ Returns the current active Juju environment """
        try:
            return check_output(['juju', 'switch'], stderr=STDOUT).rstrip()
        except CalledProcessError as ex:
            print ex.output
            raise

    @staticmethod
    def create(name, bootstrap_host, juju_config, machines):
        """Creates Juju environment, add all available machines,
        deploy juju_gui"""
        JujuEnvironment._create_env(name, bootstrap_host, juju_config)
        # Wait 5 seconds before adding machines because python
        # is too fast for juju
        sleep(5)
        environment = JujuEnvironment(name)
        sleep(5)
        environment.add_machines(machines)
        environment.deploy_gui()

    @staticmethod
    def _create_env(name, bootstrap_host, juju_config):
        """ Add new Juju environment with name = name
        and bootstrap this environment """
        print "adding juju environment %s" % name
        juju_config['bootstrap-host'] = bootstrap_host
        # get original environments config
        with open(expanduser("~/.juju/environments.yaml"), 'r') as config_file:
            config = yaml.load(config_file)
        if config['environments'] == None:
            config['environments'] = dict()
        # add new environment
        config['environments'][name] = juju_config
        # write new environments config
        with open(expanduser("~/.juju/environments.yaml"), 'w') as config_file:
            config_file.write(yaml.dump(config, default_flow_style=False))
        # Bootstrap new environmnent
        try:
            check_output(['juju', 'switch', name], stderr=STDOUT)
            print "bootstrapping juju environment"
            sleep(5) # otherwise we get a weird error
            check_output(['juju', 'bootstrap'], stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise
