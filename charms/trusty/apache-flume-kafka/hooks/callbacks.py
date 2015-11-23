import re
from subprocess import check_output

import jujuresources
from charmhelpers.core import hookenv, templating
from charmhelpers.core import host
from charmhelpers.core import unitdata
from jujubigdata import utils
from jujubigdata.relations import FlumeAgent, Kafka


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
    # Report blocked if missing config, regardless of our charm.active flag
    if not hookenv.config()['kafka_topic']:
        hookenv.status_set('blocked', 'Missing kafka_topic config value')
        return True
    elif not hookenv.config()['zookeeper_connect']:
        hookenv.status_set('blocked', 'Missing zookeeper_connect config value')
        return True

    # If we're active, there's no need to test relations
    if unitdata.kv().get('charm.active', False):
        return True

    # If we've made it this far, we've got config but aren't yet active.
    # Make sure we've got required (and ready) relations.
    if not FlumeAgent().connected_units():
        hookenv.status_set('blocked', 'Waiting for relation to apache-flume-hdfs')
    elif not FlumeAgent().is_ready():
        hookenv.status_set('waiting', 'Waiting for Flume/HDFS to become ready')
    if not Kafka().connected_units():
        hookenv.status_set('blocked', 'Waiting for relation to apache-kafka')
    elif not Kafka().is_ready():
        hookenv.status_set('waiting', 'Waiting for Kafka to become ready')
    return True


def update_working_status():
    if unitdata.kv().get('charm.active', False):
        hookenv.status_set('maintenance', 'Updating configuration')
        return
    hookenv.status_set('maintenance', 'Setting up Flume/Kafka')


def update_active_status():
    unitdata.kv().set('charm.active', True)
    # The charm may be active from a 'relation' standpoint, but report blocked
    # if we're missing required config.
    if not hookenv.config()['kafka_topic']:
        hookenv.status_set('blocked', 'Missing kafka_topic config value')
    elif not hookenv.config()['zookeeper_connect']:
        hookenv.status_set('blocked', 'Missing zookeeper_connect config value')
    else:
        hookenv.status_set('active', 'Ready')


def clear_active_flag():
    unitdata.kv().set('charm.active', False)


# Main Flume-Kafka class for callbacks
class Flume(object):
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.resources = {
            'flume': 'flume-%s' % host.cpu_arch(),
            'zookeeper': 'zookeeper-%s' % host.cpu_arch(),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def is_installed(self):
        return unitdata.kv().get('flume_kafka.installed')

    def install(self, force=False):
        if not force and self.is_installed():
            return
        jujuresources.install(self.resources['flume'],
                              destination=self.dist_config.path('flume'),
                              skip_top_level=True)
        # FlumeSource needs the zookeeper jars
        jujuresources.install(self.resources['zookeeper'],
                              destination=self.dist_config.path('zookeeper'),
                              skip_top_level=True)
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        self.setup_flume_config()
        self.configure_flume()
        unitdata.kv().set('flume_kafka.installed', True)

    def setup_flume_config(self):
        '''
        copy the default configuration files to flume_conf property
        defined in dist.yaml
        '''
        default_conf = self.dist_config.path('flume') / 'conf'
        flume_conf = self.dist_config.path('flume_conf')
        flume_conf.rmtree_p()
        default_conf.copytree(flume_conf)
        # Now remove the conf included in the tarball and symlink our real conf
        default_conf.rmtree_p()
        flume_conf.symlink(default_conf)

        flume_env = self.dist_config.path('flume_conf') / 'flume-env.sh'
        if not flume_env.exists():
            (self.dist_config.path('flume_conf') / 'flume-env.sh.template').copy(flume_env)
        utils.re_edit_in_place(flume_env, {
            r'.*FLUME_CLASSPATH.*': 'FLUME_CLASSPATH={}/*'.format(self.dist_config.path('zookeeper')),
        })

        flume_conf = self.dist_config.path('flume_conf') / 'flume.conf'
        if not flume_conf.exists():
            (self.dist_config.path('flume_conf') / 'flume-conf.properties.template').copy(flume_conf)

        flume_log4j = self.dist_config.path('flume_conf') / 'log4j.properties'
        utils.re_edit_in_place(flume_log4j, {
            r'^flume.log.dir.*': 'flume.log.dir={}'.format(self.dist_config.path('flume_logs')),
        })
        # fix for lxc containers and some corner cases in manual provider
        utils.update_etc_hosts({hookenv.unit_private_ip():hostname()})
        templating.render(
            'upstart.conf',
            '/etc/init/flume.conf',
            context={
                'flume': self.dist_config.path('flume'),
                'flume_conf': self.dist_config.path('flume_conf')
            },
        )

    def configure_flume(self):
        flume_bin = self.dist_config.path('flume') / 'bin'
        java_symlink = check_output(["readlink", "-f", "/usr/bin/java"])
        java_home = re.sub('/bin/java', '', java_symlink).rstrip()
        java_cp = "{}".format(self.dist_config.path('flume') / 'lib')
        with utils.environment_edit_in_place('/etc/environment') as env:
            if flume_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], flume_bin])
            env['FLUME_CONF_DIR'] = self.dist_config.path('flume_conf')
            env['FLUME_CLASSPATH'] = java_cp
            env['FLUME_HOME'] = self.dist_config.path('flume')
            env['JAVA_HOME'] = java_home

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        host.service_start('flume')

    def stop(self):
        host.service_stop('flume')

    def cleanup(self):
        self.dist_config.remove_users()
        self.dist_config.remove_dirs()
