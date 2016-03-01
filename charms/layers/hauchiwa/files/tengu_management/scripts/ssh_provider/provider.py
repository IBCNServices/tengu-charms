#!/usr/bin/python3
# pylint: disable=C0111,c0321,c0301,c0325
#
""" deploys a tengu env on a general ssh reachable cluster"""
import yaml


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


class SSHEnv(object):
    def __init__(self, global_conf, env_conf):
        self.bundle_path = "{}/bundle.yaml".format(env_conf.dir)

        self.global_conf = global_conf
        self.env_conf = env_conf

    def create(self, bundle):
        with open("{}/bundle.yaml".format(self.env_conf.dir), 'w') as outfile:
            outfile.write(yaml.dump(bundle, default_flow_style=True))

    def renew(self, hours):
        print('Renew unnecessary in SSH environment...')

    def destroy(self):
        print('Nothing to destroy in SSH environment...')

    @property
    def machines(self):
        try:
            return get_machines_from_bundle(self.bundle_path)
        except IOError:
            raise ProviderException('Bundle not found')

    @property
    def status(self):
        # TODO implement status ping check
        return 'TODO status'


def get_machines_from_bundle(bundle):
    machines = bundle.get('machines')
    machines_list = list()
    if not machines: raise Exception('Could not find machines item in bundle.')
    if not len(machines) > 0: raise Exception('There has to be at least 1 machine specified')
    for m_id in range(len(machines)):
        if not machines.get(str(m_id)): raise Exception(
            'machine {} not found while number of machines is {}.'.format(m_id, len(machines)))
        if m_id == 0:
            machines_list.append(machines[str(m_id)].get('host'))
    return machines_list
