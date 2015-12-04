# pylint: disable=c0111,r0201
#
""" Handles communication to Juju """

from os.path import expanduser
from subprocess import check_output, STDOUT, CalledProcessError, PIPE, Popen
from time import sleep
import yaml
# self written modules and classes
import json

class JujuEnvironment(object):
    """ handles an existing Juju environment """
    def __init__(self, _name):
        if _name:
            self.name = _name
            switch_env(self.name)
        else:
            self.name = current_env()


    def get_machine_id(self, fqdn):
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
    def status(self):
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
        for machinefqdn in machines:
            print '\t %s' % machinefqdn
            try:
                check_output(['juju',
                              'add-machine',
                              'ssh:%s' % self.bootstrap_user +
                              '@%s' % machinefqdn],
                             stderr=STDOUT)
            except CalledProcessError as ex:
                print ex.output
                raise


    def deploy_gui(self):
        """ Deploys juju-gui to node 0 """
        try:
            check_output(['juju', 'deploy', 'juju-gui', '--to', '0'],
                         stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def deploy(self, charm, name, config_path=None, to=None): #pylint: disable=c0103
        """ Deploy <charm> as <name> with config in <config_path> """
        c_action = ['juju', 'deploy']
        c_charm = [charm, name]
        c_config = []
        c_to = []
        if config_path:
            c_config = ['--config', config_path]
        if to:
            c_to = ['--to', to]
        command = c_action + c_charm + c_config + c_to
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def deploy_bundle(self, bundle_path):
        """ Deploy Juju bundle """
        c_action = ['juju', 'deployer']
        c_bundle = ['-c', bundle_path]
        command = c_action + c_bundle
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def action_do(self, unit, action, **kwargs):
        c_action = ['juju', 'action', 'do', str(unit), str(action)]
        c_params = []
        for key, value in kwargs.iteritems():
            c_params.append("{}={}".format(key, value))
        command = c_action + c_params
        try:
            print str(command)
            return check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def destroy_service(self, name):
        """ Deploy <charm> as <name> with config in <config_path> """
        c_action = ['juju', 'destroy']
        c_charm = [name]
        c_force = ['--force']
        command = c_action + c_charm + c_force
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise

    def add_relation(self, charm1, charm2):
        """ add relation between two charms """
        c_action = ['juju', 'add-relation']
        c_relations = [charm1, charm2]
        command = c_action + c_relations
        try:
            check_output(command, stderr=STDOUT)
        except CalledProcessError as ex:
            print ex.output
            raise


    def charm_exists(self, name):
        return name in self.status['services']


def switch_env(name):
    """switch to environment with given name"""
    try:
        check_output(['juju', 'switch', name], stderr=STDOUT)
    except CalledProcessError as ex:
        print ex.output
        raise

def env_exists(name):
    """Checks if Juju env with given name exists."""
    try:
        envs = check_output(['juju', 'switch', '--list'],
                            stderr=STDOUT).split()
    except CalledProcessError as ex:
        print ex.output
        raise
    return name in envs

def current_env():
    """ Returns the current active Juju environment """
    try:
        return check_output(['juju', 'switch'], stderr=STDOUT).rstrip()
    except CalledProcessError as ex:
        print ex.output
        raise

def create(name, bootstrap_host, juju_config, machines):
    """Creates Juju environment, add all available machines,
    deploy juju_gui"""
    _create_env(name, bootstrap_host, juju_config)
    # Wait 5 seconds before adding machines because python
    # is too fast for juju
    sleep(5)
    environment = JujuEnvironment(name)
    environment.add_machines(machines)
    environment.deploy_gui()

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
        check_output(['juju', 'set-environment', 'default-series=trusty'],
                     stderr=STDOUT)
    except CalledProcessError as ex:
        print ex.output
        raise
