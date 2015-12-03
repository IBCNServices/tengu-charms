#pylint: disable=c0301,c0111,r0201
import os
from subprocess import Popen, check_output

import jujuresources
from charmhelpers.core import hookenv, templating
from charmhelpers.core import host
from charmhelpers.core import unitdata
from jujubigdata import utils
from jujubigdata.relations import Zookeeper


# This should be in charmhelpers.core.host
def hostname():
    """ Returns fqdn for host """
    return check_output(['hostname']).rstrip()


# Extended status support
# We call update_blocked_status from the "requires" section of our service
# block, so be sure to return True. Otherwise, we'll block the "requires"
# and never move on to callbacks. The other status update methods are called
# from the "callbacks" section and therefore don't need to return True.
def update_blocked_status():
    if unitdata.kv().get('charm.active', False):
        return True
    if not Zookeeper().connected_units():
        hookenv.status_set(
            'blocked', 'Waiting for relation to apache-zookeeper')
    elif not Zookeeper().is_ready():
        hookenv.status_set('waiting', 'Waiting for Zookeeper to become ready')
    return True


def update_working_status():
    if unitdata.kv().get('charm.active', False):
        hookenv.status_set('maintenance', 'Updating configuration')
        return
    hookenv.status_set('maintenance', 'Setting up Apache Kafka')


def update_active_status():
    unitdata.kv().set('charm.active', True)
    hookenv.status_set('active', 'Ready')


def clear_active_flag():
    unitdata.kv().set('charm.active', False)


# Main Kafka class for callbacks
class Kafka(object):
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.resources = {
            'kafka': 'kafka-%s' % host.cpu_arch(),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def is_installed(self):
        return unitdata.kv().get('kafka.installed')

    def install(self, force=False):
        if not force and self.is_installed():
            return
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        jujuresources.install(self.resources['kafka'],
                              destination=self.dist_config.path('kafka'),
                              skip_top_level=True)
        self.setup_kafka_config()
        unitdata.kv().set('kafka.installed', True)

    def setup_kafka_config(self):
        '''
        copy the default configuration files to kafka_conf property
        defined in dist.yaml
        '''
        default_conf = self.dist_config.path('kafka') / 'config'
        kafka_conf = self.dist_config.path('kafka_conf')
        kafka_conf.rmtree_p()
        default_conf.copytree(kafka_conf)
        # Now remove the conf included in the tarball and symlink our real conf
        # dir. we've seen issues where kafka still looks for config in
        # KAFKA_HOME/config.
        default_conf.rmtree_p()
        kafka_conf.symlink(default_conf)

        # Configure immutable bits
        kafka_bin = self.dist_config.path('kafka') / 'bin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            if kafka_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], kafka_bin])
            env['LOG_DIR'] = self.dist_config.path('kafka_app_logs')

        kafka_server_conf = self.dist_config.path('kafka_conf') / 'server.properties'
        service, unit_num = os.environ['JUJU_UNIT_NAME'].split('/', 1)
        utils.re_edit_in_place(kafka_server_conf, {
            r'^broker.id=.*': 'broker.id=%s' % unit_num,
            r'^port=.*': 'port=%s' % self.dist_config.port('kafka'),
            r'^log.dirs=.*': 'log.dirs=%s' % self.dist_config.path('kafka_data_logs'),
            r'^#?advertised.host.name=.*': 'advertised.host.name=%s' % hookenv.unit_private_ip(),
        })

        kafka_log4j = self.dist_config.path('kafka_conf') / 'log4j.properties'
        utils.re_edit_in_place(kafka_log4j, {
            r'^kafka.logs.dir=.*': 'kafka.logs.dir=%s' % self.dist_config.path('kafka_app_logs'),
        })
        # fix for lxc containers and some corner cases in manual provider
        ip_addr = utils.resolve_private_address(utils.unit_private_ip())
        utils.update_etc_hosts({
            ip_addr:hostname()
        })
        templating.render(
            'upstart.conf',
            '/etc/init/kafka.conf',
            context={
                'kafka_conf':self.dist_config.path('kafka_conf'),
                'kafka_bin':'{}/bin'.format(self.dist_config.path('kafka'))
            },
        )

    def configure_kafka(self):
        # Get ip:port data from our connected zookeepers
        if Zookeeper().connected_units() and Zookeeper().is_ready():
            zks = []
            for unit, data in Zookeeper().filtered_data().items():
                zk_ip = utils.resolve_private_address(data['private-address'])
                zks.append("%s:%s" % (zk_ip, data['port']))
            zks.sort()
            zk_connect = ",".join(zks)

            # update consumer props
            cfg = self.dist_config.path('kafka_conf') / 'consumer.properties'
            utils.re_edit_in_place(cfg, {
                r'^zookeeper.connect=.*': 'zookeeper.connect=%s' % zk_connect,
            })

            # update server props
            cfg = self.dist_config.path('kafka_conf') / 'server.properties'
            utils.re_edit_in_place(cfg, {
                r'^zookeeper.connect=.*': 'zookeeper.connect=%s' % zk_connect,
            })
        else:
            # if we have no zookeepers, make sure kafka is stopped
            self.stop()

    def run_bg(self, user, command, *args):
        """
        Run a Kafka command as the `kafka` user in the background.

        :param str command: Command to run
        :param list args: Additional args to pass to the command
        """
        parts = [command] + list(args)
        quoted = ' '.join("'%s'" % p for p in parts)
        env = utils.read_etc_env()
        Popen(['su', user, '-c', quoted], env=env)

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        host.service_start('kafka')

    def stop(self):
        host.service_stop('kafka')

    def cleanup(self):
        self.dist_config.remove_users()
        self.dist_config.remove_dirs()
