# pylint: disable=C0111,R0201,C0301
import jujuresources
from charmhelpers.core import hookenv, templating, host


import os
import Path
from subprocess import check_output, check_call
from tempfile import NamedTemporaryFile

def read_etc_env():
    """
    Read /etc/environment and return it, along with proxy configuration, as
    a dict.
    """
    env = {}

    # Proxy config (e.g. https_proxy, no_proxy, etc) is not stored in
    # /etc/environment on a Juju unit, but we should pass it along so anyone
    # using this env will have correct proxy settings.
    env.update({k: v for k, v in os.environ.items()
                if k.lower().endswith('_proxy')})

    etc_env = Path('/etc/environment')
    if etc_env.exists():
        for line in etc_env.lines():
            var, value = line.split('=', 1)
            env[var.strip()] = value.strip(' \'"')
    return env

def run_as(user, command, *args, **kwargs):
    """
    Run a command as a particular user, using ``/etc/environment`` and optionally
    capturing and returning the output.
    Raises subprocess.CalledProcessError if command fails.
    :param str user: Username to run command as
    :param str command: Command to run
    :param list args: Additional args to pass to command
    :param dict env: Additional env variables (will be merged with ``/etc/environment``)
    :param bool capture_output: Capture and return output (default: False)
    :param str input: Stdin for command
    """
    parts = [command] + list(args)
    quoted = ' '.join("'%s'" % p for p in parts)
    env = read_etc_env()
    if 'env' in kwargs:
        env.update(kwargs['env'])
    run = check_output if kwargs.get('capture_output') else check_call
    try:
        stdin = None
        if 'input' in kwargs:
            stdin = NamedTemporaryFile()
            stdin.write(kwargs['input'])
            stdin.seek(0)
        return run(['su', user, '-c', quoted], env=env, stdin=stdin)
    finally:
        if stdin:
            stdin.close()  # this also removes tempfile



class Hue(object):
    def __init__(self):
        self.dist_config = utils.DistConfig(
            filename='dist.yaml',
            required_keys=['packages', 'groups', 'users', 'dirs'])
        self.resources = {
            'hue': 'hue-x86_64',
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def install(self):
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        jujuresources.install(self.resources['hue'],
                              destination=self.dist_config.path('build'),
                              skip_top_level=True)
    #ln -s /usr/lib/python2.7/plat-*/_sysconfigdata_nd.py /usr/lib/python2.7/
        run_as(
            'root',
            'make', '-C', self.dist_config.path('build'), 'install',
            env={
                'PREFIX' : self.dist_config.path('hue') + "/../",
            }
        )
        templating.render(
            'upstart.conf',
            '/etc/init/hue.conf',
            context={
                'hue': self.dist_config.path('hue'),
                'hue_connect': '{}:{}'.format(hookenv.unit_private_ip(), '8000')
            },
        )


    def configure(self):
        pass

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        host.service_start('hue')

    def stop(self):
        host.service_stop('hue')

    def cleanup(self):
        self.dist_config.remove_users()
        self.dist_config.remove_dirs()

    def open_ports(self):
        for port in self.dist_config.exposed_ports('hue'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('hue'):
            hookenv.close_port(port)

    @property
    def hue_ini(self):
        return self.dist_config.path('hue_conf') + "/hue.ini"
