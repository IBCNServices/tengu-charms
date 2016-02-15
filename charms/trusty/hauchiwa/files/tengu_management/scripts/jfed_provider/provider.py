#!/usr/bin/python
# pylint: disable=C0111,c0321,c0301,c0325
#
""" deploys a tengu env """
from os.path import expanduser

# non-default pip dependencies
import yaml

# Own modules
from rest2jfed_connector import Rest2jfedConnector
import rspec_utils

TENGU_DIR = expanduser("~/.tengu")

class ProviderException(Exception):
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
    with open(bundle_path, 'r') as bundle_file:
        bundle = yaml.load(bundle_file)
    return len(bundle['machines'])


def get_data_from_bundle(bundle):
    machines = bundle.get('machines')
    if not machines: raise Exception('Could not find machines item in bundle.')
    if not len(machines) > 0: raise Exception('There has to be at least 1 machine specified')
    testbed = None
    pub_ipv4 = False
    for m_id in range(len(machines)):
        if not machines.get(str(m_id)): raise Exception('machine {} not found while number of machines is {}.'.format(m_id, len(machines)))
        if m_id == 0:
            constraints = machines[str(m_id)].get('constraints').split()
            for constraint in constraints:
                if constraint.startswith('testbed='):
                    testbed = constraint.split('=')[1]
                elif constraint.startswith('pubipv4=') and constraint.split('=')[1].lower() == 'true':
                    pub_ipv4 = True
            if not testbed: raise Exception("machine {} doesn't specify testbed.".format(m_id))
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
