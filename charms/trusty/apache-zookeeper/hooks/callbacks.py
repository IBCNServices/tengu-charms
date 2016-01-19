import jujuresources
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers.core import unitdata
from jujubigdata import utils
from zkutils import update_zoo_cfg, getid


# Extended status support
def update_working_status():
    if unitdata.kv().get('charm.active', False):
        hookenv.status_set('maintenance', 'Updating configuration')
        return
    hookenv.status_set('maintenance', 'Setting up Zookeeper')


def update_active_status():
    unitdata.kv().set('charm.active', True)
    hookenv.status_set('active', 'Ready')


# Main Zookeeper class for callbacks
class Zookeeper(object):
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.resources = {
            'zookeeper': 'zookeeper-%s' % host.cpu_arch(),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def is_installed(self):
        return unitdata.kv().get('zookeeper.installed')

    def install(self, force=False):
        if not force and self.is_installed():
            return

        jujuresources.install(self.resources['zookeeper'],
                              destination=self.dist_config.path('zookeeper'),
                              skip_top_level=True)

        self.dist_config.add_users()
        utils.disable_firewall()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        self.setup_zookeeper_config()
        self.configure_zookeeper()
        unitdata.kv().set('zookeeper.installed', True)

    def setup_zookeeper_config(self):
        '''
        copy the default configuration files to zookeeper_conf property
        defined in dist.yaml
        '''
        default_conf = self.dist_config.path('zookeeper') / 'conf'
        zookeeper_conf = self.dist_config.path('zookeeper_conf')
        zookeeper_conf.rmtree_p()
        default_conf.copytree(zookeeper_conf)
        # Now remove the conf included in the tarball and symlink our real conf
        default_conf.rmtree_p()
        zookeeper_conf.symlink(default_conf)

        zoo_cfg = zookeeper_conf / 'zoo.cfg'
        if not zoo_cfg.exists():
            (zookeeper_conf / 'zoo_sample.cfg').copy(zoo_cfg)
        utils.re_edit_in_place(zoo_cfg, {
            r'^dataDir.*': 'dataDir={}'.format(self.dist_config.path('zookeeper_data_dir')),
        })

        # Configure zookeeper environment for all users
        zookeeper_bin = self.dist_config.path('zookeeper') / 'bin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            if zookeeper_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], zookeeper_bin])
            env['ZOOCFGDIR'] = self.dist_config.path('zookeeper_conf')
            env['ZOO_BIN_DIR'] = zookeeper_bin
            env['ZOO_LOG_DIR'] = self.dist_config.path('zookeeper_log_dir')

    def configure_zookeeper(self):
        '''
        The entries of the form server.X list the servers that make up the ZooKeeper
        service. When the server starts up, it knows which server it is by looking for
        the file myid in the data directory. That file contains the unit number
        in ASCII.
        '''
        myid = self.dist_config.path('zookeeper_data_dir') / 'myid'
        with open(myid, 'w+') as df:
            df.writelines(getid(hookenv.local_unit()))

        # update_zoo_cfg maintains a server.X entry in this unit's zoo.cfg
        update_zoo_cfg()

    def start(self):
        zookeeper_home = self.dist_config.path('zookeeper')
        self.stop()
        utils.run_as('zookeeper', '{}/bin/zkServer.sh'.format(zookeeper_home), 'start')

    def stop(self):
        zookeeper_home = self.dist_config.path('zookeeper')
        utils.run_as('zookeeper', '{}/bin/zkServer.sh'.format(zookeeper_home), 'stop')

    def cleanup(self):
        self.dist_config.remove_dirs()
        unitdata.kv().set('zookeeper.installed', False)
