# pylint: disable=C0111,R0201,C0301
import string
import random

import jujuresources
from jujubigdata.utils import re_edit_in_place

from charmhelpers.core import hookenv, templating, host

class Hue(object):
    def __init__(self):
        from jujubigdata import utils
        self.dist_config = utils.DistConfig(
            filename='dist.yaml',
            required_keys=['packages', 'groups', 'users', 'dirs'])
        self.resources = {
            'hue': 'hue-x86_64',
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def install(self):
        from jujubigdata import utils
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        jujuresources.install(self.resources['hue'],
                              destination=self.dist_config.path('build'),
                              skip_top_level=True)
        #ln -s /usr/lib/python2.7/plat-*/_sysconfigdata_nd.py /usr/lib/python2.7/
        utils.run_as(
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
        randomstring = ''.join(random.SystemRandom().choice(
            string.ascii_letters + string.digits) for _ in range(20)
        )
        re_edit_in_place(self.hue_ini, {
            r'^\s*#*\s*desktop.secret_key=.*' : "      desktop.secret_key={}".format(randomstring),
        })

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
        #for port in self.dist_config.exposed_ports('hue'):
        hookenv.open_port('8000')

    def close_ports(self):
        #for port in self.dist_config.exposed_ports('hue'):
        hookenv.close_port('8000')

    @property
    def hue_ini(self):
        return '/usr/share/hue/desktop/conf' + "/hue.ini"
