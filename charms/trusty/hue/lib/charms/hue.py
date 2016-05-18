#python3 pylint:disable=c0301,c0111,R0914,R0201
import os
import uuid
import subprocess

import yaml

import jujuresources
from jujubigdata import utils
from charmhelpers.core import unitdata, hookenv
from charmhelpers.core.host import chownr
from charms.reactive.bus import get_states


class Hue(object):

    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.cpu_arch = utils.cpu_arch()
        self.resources = {
            'hue': 'hue-{}'.format(self.cpu_arch),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())
        self.hue_config = ''.join((self.dist_config.path('hue'), '/desktop/conf/hue.ini'))

    def install(self):
        jujuresources.install(self.resources['hue'],
                              destination=self.dist_config.path('hue'),
                              skip_top_level=True)

        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        chownr(self.dist_config.path('hue'), 'hue', 'hadoop')
        unitdata.kv().set('hue.installed', True)

    def check_relations(self):
        '''
        This function checks the 'additional_relations' list against the joined
        relation states so we don't have to explicitly set_status in each reactive
        function
        '''
        additional_relations = []
        metadata_stream = open('metadata.yaml', 'r')
        data = yaml.load(metadata_stream)
        for key in data['requires']:
            additional_relations.append(key)
        current_relations = additional_relations
        all_states = get_states()
        for key in all_states:
            if "joined" in key:
                relname = key.split('.')[0]
                if relname in additional_relations:
                    current_relations.remove(relname)

        wait_rels = ', '.join(current_relations)
        if len(current_relations) > 0:
            hookenv.status_set('active', 'Ready. Accepting connections to {}'.format(wait_rels))
        else:
            hookenv.status_set('active', 'Ready')

    def setup_hue(self, namenodes, resourcemanagers, hdfs_port, yarn_port):
        hookenv.status_set('maintenance', 'Setting up Hue')
        hue_bin = self.dist_config.path('hue') / 'bin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            if hue_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], hue_bin])
            env['HADOOP_BIN_DIR'] = env['HADOOP_HOME'] + '/bin'
            env['GOBBLIN_WORK_DIR'] = self.dist_config.path('outputdir')
            yarn_conf = env['HADOOP_CONF_DIR'] + '/yarn-site.xml'


        with utils.xmlpropmap_edit_in_place(yarn_conf) as props:
            yarn_log_url = props['yarn.log.server.url'] # 19888
            yarn_resmgr = props['yarn.resourcemanager.address'] # 8032

        default_conf = self.dist_config.path('hue') / 'desktop/conf'
        hue_conf = self.dist_config.path('hue_conf')

        if os.path.islink('/usr/lib/hue/desktop/conf'):
            return
        else:
            hue_conf.rmtree_p()
            default_conf.copytree(hue_conf)
            # Now remove the conf included in the tarball and symlink our real conf
            default_conf.rmtree_p()
            hue_conf.symlink(default_conf)

        hue_port = self.dist_config.port('hue_web')

        # Fix following for HA: http://docs.hortonworks.com/HDPDocuments/HDP2/HDP-2.3.0/bk_hadoop-ha/content/ha-nn-deploy-hue.html
        hookenv.log("Not currently supporting HA, FIX: namenodes are: " + str(namenodes) + " resmanagers: " + str(resourcemanagers))
        utils.re_edit_in_place(self.hue_config, {
            r'http_port=8888': 'http_port={}' % hue_port,
            r'fs_defaultfs=hdfs://localhost:8020': 'fs_defaultfs={}:{}'.format(namenodes[0], hdfs_port),
            r'.*resourcemanager_host=localhost': 'resourcemanager_host={}'.format(resourcemanagers[0]),
            r'.*resourcemanager_port=8032': 'resourcemanager_port={}'.format(yarn_port),
            r'.*webhdfs_url=http://localhost:50070/webhdfs/v1': 'webhdfs_url=http://{}:50070/webhdfs/v1'.format(namenodes[0]),
            r'.*history_server_api_url=http://localhost:19888': 'history_server_api_url={}'.format(yarn_log_url.split('/')[0]),
            r'.*resourcemanager_api_url=http://localhost:8088': 'resourcemanager_api_url=http://{}:8088'.format(yarn_resmgr.split(':')[0]),
            r'.*secret_key=.*': 'secret_key={}'.format(uuid.uuid4())
            })

        self.update_apps()

    def open_ports(self):
        for port in self.dist_config.exposed_ports('hue'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('hue'):
            hookenv.close_port(port)

    def update_apps(self):
        # Add all services disabled unless we have a joined relation
        # as marked by the respective state
        # Enabled by default: 'filebrowser', 'jobbrowser'
        disabled_services = [
            'beeswax', 'impala', 'security',
            'rdbms', 'jobsub', 'pig', 'hbase', 'sqoop',
            'zookeeper', 'metastore', 'spark', 'oozie', 'indexer', 'search']

        for key in get_states():
            if "joined" in key:
                relname = key.split('.')[0]
                if 'hive' in relname:
                    disabled_services.remove('beeswax')
                    disabled_services.remove('metastore')
                if 'spark' in relname:
                    disabled_services.remove('spark')
                if 'oozie' in relname:
                    disabled_services.remove('oozie')
                if 'zookeeper' in relname:
                    disabled_services.remove('zookeeper')

        hue_config = ''.join((self.dist_config.path('hue'), '/desktop/conf/hue.ini'))
        services_string = ','.join(disabled_services)
        hookenv.log("Disabled apps {}".format(services_string))
        utils.re_edit_in_place(hue_config, {
            r'.*app_blacklist=.*': ''.join(('app_blacklist=', services_string))
            })

        self.check_relations()

    def start(self):
        self.stop()
        hookenv.log("Starting HUE with Supervisor process")
        hue_log = self.dist_config.path('hue_log')
        utils.run_as('hue', '/usr/lib/hue/build/env/bin/supervisor', '-l', hue_log, '-d')

    def stop(self):
        hookenv.log("Stopping HUE and Supervisor process")
        try:
            utils.run_as('hue', 'pkill', '-9', 'supervisor')
            utils.run_as('hue', 'pkill', '-9', 'hue')
        except subprocess.CalledProcessError:
            return

    def soft_restart(self):
        hookenv.log("Restarting HUE with Supervisor process")
        try:
            utils.run_as('hue', 'pkill', '-9', 'hue')
        except subprocess.CalledProcessError:
            hookenv.log("Problem with Supervisor process, doing hard HUE restart")
            self.stop()
            self.start()

    def restart(self):
        hookenv.log("Restarting HUE")
        self.stop()
        self.start()

    def configure_hive(self, hostname, port):
        hookenv.log("configuring hive connection")
        utils.re_edit_in_place(self.hue_config, {
            r'.*hive_server_host *=.*': 'hive_server_host={}'.format(hostname),
            r'.*hive_server_port *=.*': 'hive_server_port={}'.format(port)
            })

    def configure_oozie(self, hostname, port):
        hookenv.log("configuring oozie connection")
        utils.re_edit_in_place(self.hue_config, {
            r'.*oozie_url *=.*': 'oozie_url=http://{}:{}/oozie'.format(hostname, port),
            })

    def configure_zookeeper(self, zookeepers):
        hookenv.log("configuring zookeeper connection")
        zks_endpoints = []
        for zookeeper in zookeepers:
            zks_endpoints.append('{}:{}'.format(zookeeper['host'], zookeeper['port']))

        ensemble = ','.join(zks_endpoints)

        zk_rest_url = "http://{}:{}".format(zookeepers[0]['host'],
                                            zookeepers[0]['rest_port'])
        hue_config = ''.join((self.dist_config.path('hue'), '/desktop/conf/hue.ini'))
        utils.re_edit_in_place(hue_config, {
            r'.*host_ports=.*': 'host_ports={}'.format(ensemble),
            r'.*rest_url=.*': 'rest_url={}'.format(zk_rest_url),
            r'.*ensemble=.*': 'ensemble={}'.format(ensemble)
            })

    def configure_spark(self, hostname, port):
        hookenv.log("configuring spark connection via livy")
        utils.re_edit_in_place(self.hue_config, {
            r'.*livy_server_host *=.*': 'livy_server_host={}'.format(hostname),
            r'.*livy_server_port *=.*': 'livy_server_port={}'.format(port)
            })

    def configure_impala(self):
        hookenv.log("configuring impala connection")

    def configure_sqoop(self):
        hookenv.log("configuring sqoop connection")

    def configure_hbase(self):
        hookenv.log("configuring hbase connection")

    def configure_solr(self):
        hookenv.log("configuring solr connection")

    def configure_aws(self):
        hookenv.log("configuring AWS connection")

    def configure_sentry(self):
        hookenv.log("configuring sentry connection")
