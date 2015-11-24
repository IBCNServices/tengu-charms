# Copyright 2014-2015 Canonical Limited.
#
# This file is part of jujubigdata.
#
# jujubigdata is free software: you can redistribute it and/or modify
# it under the terms of the Apache License version 2.0.
#
# jujubigdata is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.

from subprocess import check_call, check_output
import time

from path import Path

import jujuresources

from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata

try:
    from charmhelpers.core.charmframework import helpers
except ImportError:
    helpers = None  # hack-around until transition to layers is complete


from jujubigdata import utils


class HadoopBase(object):
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.charm_config = hookenv.config()
        self.cpu_arch = host.cpu_arch()
        self.client_spec = {
            'hadoop': self.dist_config.hadoop_version,
        }

        # dist_config will have simple validation done on primary keys in the
        # dist.yaml, but we need to ensure deeper values are present.
        required_dirs = ['hadoop', 'hadoop_conf', 'hdfs_log_dir',
                         'yarn_log_dir']
        missing_dirs = set(required_dirs) - set(self.dist_config.dirs.keys())
        if missing_dirs:
            raise ValueError('dirs option in {} is missing required entr{}: {}'.format(
                self.dist_config.yaml_file,
                'ies' if len(missing_dirs) > 1 else 'y',
                ', '.join(missing_dirs)))

        # Build a list of hadoop resources needed from resources.yaml
        hadoop_resources = []
        hadoop_version = self.dist_config.hadoop_version
        try:
            jujuresources.resource_path('hadoop-%s-%s' % (hadoop_version, self.cpu_arch))
            hadoop_resources.append('hadoop-%s-%s' % (hadoop_version, self.cpu_arch))
        except KeyError:
            hadoop_resources.append('hadoop-%s' % (self.cpu_arch))

        # LZO compression for hadoop is distributed separately. Add it to the
        # list of reqs if defined in resources.yaml
        try:
            jujuresources.resource_path('hadoop-lzo-%s' % self.cpu_arch)
            hadoop_resources.append('hadoop-lzo-%s' % (self.cpu_arch))
        except KeyError:
            pass

        # Verify and fetch the required hadoop resources
        self.verify_conditional_resources = utils.verify_resources(*hadoop_resources)

    def spec(self):
        """
        Generate the full spec for keeping charms in sync.

        NB: This has to be a callback instead of a plain property because it is
        passed to the relations during construction of the Manager but needs to
        properly reflect the Java version in the same hook invocation that installs
        Java.
        """
        java_version = unitdata.kv().get('java.version')
        if java_version:
            return {
                'vendor': self.dist_config.vendor,
                'hadoop': self.dist_config.hadoop_version,
                'java': java_version,
                'arch': self.cpu_arch,
            }
        else:
            return None

    def is_installed(self):
        return unitdata.kv().get('hadoop.base.installed')

    def install(self, force=False):
        if not force and self.is_installed():
            return
        hookenv.status_set('maintenance', 'Installing Apache Hadoop base')
        self.configure_hosts_file()
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        self.install_base_packages()
        self.setup_hadoop_config()
        self.configure_hadoop()
        unitdata.kv().set('hadoop.base.installed', True)
        unitdata.kv().flush(True)
        hookenv.status_set('waiting', 'Apache Hadoop base installed')

    def configure_hosts_file(self):
        """
        Add the unit's private-address to /etc/hosts to ensure that Java
        can resolve the hostname of the server to its real IP address.
        We derive our hostname from the unit_id, replacing / with -.
        """
        local_ip = utils.resolve_private_address(hookenv.unit_get('private-address'))
        hostname = hookenv.local_unit().replace('/', '-')
        utils.update_etc_hosts({local_ip: hostname})

        # update name of host to more semantically meaningful value
        # (this is required on some providers; the /etc/hosts entry must match
        # the /etc/hostname lest Hadoop get confused about where certain things
        # should be run)
        etc_hostname = Path('/etc/hostname')
        etc_hostname.write_text(hostname)
        check_call(['hostname', '-F', etc_hostname])

    def install_base_packages(self):
        with utils.disable_firewall():
            self.install_java()
            self.install_hadoop()

    def install_java(self):
        """
        Run the java-installer resource to install Java and determine
        the JAVA_HOME and Java version.

        The java-installer must be idempotent and its only output (on stdout)
        should be two lines: the JAVA_HOME path, and the Java version, respectively.

        If there is an error installing Java, the installer should exit
        with a non-zero exit code.
        """
        env = utils.read_etc_env()
        java_installer = Path(jujuresources.resource_path('java-installer'))
        java_installer.chmod(0o755)
        output = check_output([java_installer], env=env)
        lines = map(str.strip, output.strip().split('\n'))
        if len(lines) != 2:
            raise ValueError('Unexpected output from java-installer: %s' % output)
        java_home, java_version = lines
        java_major, java_release = java_version.split("_")
        unitdata.kv().set('java.home', java_home)
        unitdata.kv().set('java.version', java_major)
        unitdata.kv().set('java.version.release', java_release)

    def install_hadoop(self):
        hadoop_version = self.dist_config.hadoop_version
        try:
            jujuresources.install('hadoop-%s-%s' %
                                  (hadoop_version,
                                   self.cpu_arch),
                                  destination=self.dist_config.path('hadoop'),
                                  skip_top_level=True)
        except KeyError:
            hookenv.log("Falling back to non-version specific download of hadoop...")
            jujuresources.install('hadoop-%s' %
                                  (self.cpu_arch),
                                  destination=self.dist_config.path('hadoop'),
                                  skip_top_level=True)

        # Install our lzo compression codec if it's defined in resources.yaml
        try:
            jujuresources.install('hadoop-lzo-%s' % self.cpu_arch,
                                  destination=self.dist_config.path('hadoop'),
                                  skip_top_level=False)
            unitdata.kv().set('hadoop.lzo.installed', True)
        except KeyError:
            msg = ("The hadoop-lzo-%s resource was not found."
                   "LZO compression will not be available." % self.cpu_arch)
            hookenv.log(msg)

    def setup_hadoop_config(self):
        # copy default config into alternate dir
        conf_dir = self.dist_config.path('hadoop') / 'etc/hadoop'
        self.dist_config.path('hadoop_conf').rmtree_p()
        conf_dir.copytree(self.dist_config.path('hadoop_conf'))
        (self.dist_config.path('hadoop_conf') / 'slaves').remove_p()
        mapred_site = self.dist_config.path('hadoop_conf') / 'mapred-site.xml'
        if not mapred_site.exists():
            (self.dist_config.path('hadoop_conf') / 'mapred-site.xml.template').copy(mapred_site)

    def configure_hadoop(self):
        java_home = Path(unitdata.kv().get('java.home'))
        java_bin = java_home / 'bin'
        hadoop_bin = self.dist_config.path('hadoop') / 'bin'
        hadoop_sbin = self.dist_config.path('hadoop') / 'sbin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            env['JAVA_HOME'] = java_home
            if java_bin not in env['PATH']:
                env['PATH'] = ':'.join([java_bin, env['PATH']])  # ensure that correct java is used
            if hadoop_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], hadoop_bin])
            if hadoop_sbin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], hadoop_sbin])
            env['HADOOP_LIBEXEC_DIR'] = self.dist_config.path('hadoop') / 'libexec'
            env['HADOOP_INSTALL'] = self.dist_config.path('hadoop')
            env['HADOOP_HOME'] = self.dist_config.path('hadoop')
            env['HADOOP_COMMON_HOME'] = self.dist_config.path('hadoop')
            env['HADOOP_HDFS_HOME'] = self.dist_config.path('hadoop')
            env['HADOOP_MAPRED_HOME'] = self.dist_config.path('hadoop')
            env['HADOOP_YARN_HOME'] = self.dist_config.path('hadoop')
            env['YARN_HOME'] = self.dist_config.path('hadoop')
            env['HADOOP_CONF_DIR'] = self.dist_config.path('hadoop_conf')
            env['YARN_CONF_DIR'] = self.dist_config.path('hadoop_conf')
            env['YARN_LOG_DIR'] = self.dist_config.path('yarn_log_dir')
            env['HDFS_LOG_DIR'] = self.dist_config.path('hdfs_log_dir')
            env['HADOOP_LOG_DIR'] = self.dist_config.path('hdfs_log_dir')  # for hadoop 2.2.0 only
            env['MAPRED_LOG_DIR'] = '/var/log/hadoop/mapred'  # should be moved to config, but could
            env['MAPRED_PID_DIR'] = '/var/run/hadoop/mapred'  # be destructive for mapreduce operation

        hadoop_env = self.dist_config.path('hadoop_conf') / 'hadoop-env.sh'
        utils.re_edit_in_place(hadoop_env, {
            r'export JAVA_HOME *=.*': 'export JAVA_HOME=%s' % java_home,
        })

    def register_slaves(self, slaves):
        """
        Add slaves to a hdfs or yarn master, determined by the relation name.

        :param str relation: 'datanode' for registering HDFS slaves;
                             'nodemanager' for registering YARN slaves.
        """
        slaves_file = self.dist_config.path('hadoop_conf') / 'slaves'
        slaves_file.write_lines(
            [
                '# DO NOT EDIT',
                '# This file is automatically managed by Juju',
            ] + slaves
        )
        slaves_file.chown('ubuntu', 'hadoop')

    def run(self, user, command, *args, **kwargs):
        """
        Run a Hadoop command as the `hdfs` user.

        :param str command: Command to run, prefixed with `bin/` or `sbin/`
        :param list args: Additional args to pass to the command
        """
        return utils.run_as(user,
                            self.dist_config.path('hadoop') / command,
                            *args, **kwargs)


class HDFS(object):
    def __init__(self, hadoop_base):
        self.hadoop_base = hadoop_base

    def stop_namenode(self):
        self._hadoop_daemon('stop', 'namenode')

    def start_namenode(self):
        if not utils.jps('NameNode'):
            self._hadoop_daemon('start', 'namenode')
            # Some hadoop processes take a bit of time to start
            # we need to let them get to a point where they are
            # ready to accept connections - increase the value for hadoop 2.4.1
            time.sleep(30)

    def stop_secondarynamenode(self):
        self._hadoop_daemon('stop', 'secondarynamenode')

    def start_secondarynamenode(self):
        if not utils.jps('SecondaryNameNode'):
            self._hadoop_daemon('start', 'secondarynamenode')
            # Some hadoop processes take a bit of time to start
            # we need to let them get to a point where they are
            # ready to accept connections - increase the value for hadoop 2.4.1
            time.sleep(30)

    def stop_datanode(self):
        self._hadoop_daemon('stop', 'datanode')

    def start_datanode(self):
        if not utils.jps('DataNode'):
            self._hadoop_daemon('start', 'datanode')

    def _remote(self, relation):
        """
        Return the hostname of the unit on the other end of the given
        relation (derived from that unit's name) and the port used to talk
        to that unit.
        :param str relation: Name of the relation, e.g. "datanode" or "namenode"
        """
        # FIXME delete when transition to layers is complete
        unit, data = helpers.any_ready_unit(relation)
        if not unit:
            return None, None
        host = unit.replace('/', '-')
        return host, data['port']

    def configure_namenode(self, secondary_host=None, secondary_port=None):
        dc = self.hadoop_base.dist_config
        host = hookenv.local_unit().replace('/', '-')
        port = dc.port('namenode')
        self.configure_hdfs_base(host, port)
        cfg = self.hadoop_base.charm_config
        hdfs_site = dc.path('hadoop_conf') / 'hdfs-site.xml'
        with utils.xmlpropmap_edit_in_place(hdfs_site) as props:
            props['dfs.replication'] = cfg['dfs_replication']
            props['dfs.blocksize'] = int(cfg['dfs_blocksize'])
            props['dfs.namenode.datanode.registration.ip-hostname-check'] = 'true'
            props['dfs.namenode.http-address'] = '0.0.0.0:{}'.format(dc.port('nn_webapp_http'))
            # TODO: support SSL
            # props['dfs.namenode.https-address'] = '0.0.0.0:{}'.format(dc.port('nn_webapp_https'))

            # FIXME hack-around until transition to layers is complete
            if not (secondary_host and secondary_port) and helpers:
                unit, secondary = helpers.any_ready_unit('secondary')
                if unit:
                    secondary_host = secondary['hostname']
                    secondary_port = secondary['port']
            if secondary_host and secondary_port:
                props['dfs.secondary.http.address'] = '{host}:{port}'.format(
                    host=secondary_host,
                    port=secondary_port,
                )

    def configure_secondarynamenode(self, host=None, port=None):
        """
        Configure the Secondary Namenode when the apache-hadoop-hdfs-secondary
        charm is deployed and related to apache-hadoop-hdfs-master.

        The only purpose of the secondary namenode is to perform periodic
        checkpoints. The secondary name-node periodically downloads current
        namenode image and edits log files, joins them into new image and
        uploads the new image back to the (primary and the only) namenode.
        """
        if not (host and port):
            host, port = self._remote("secondary")
        self.configure_hdfs_base(host, port)

    def configure_datanode(self, host=None, port=None):
        if not (host and port):
            host, port = self._remote("datanode")
        self.configure_hdfs_base(host, port)
        dc = self.hadoop_base.dist_config
        hdfs_site = dc.path('hadoop_conf') / 'hdfs-site.xml'
        with utils.xmlpropmap_edit_in_place(hdfs_site) as props:
            props['dfs.datanode.http.address'] = '0.0.0.0:{}'.format(dc.port('dn_webapp_http'))
            # TODO: support SSL
            # props['dfs.datanode.https.address'] = '0.0.0.0:{}'.format(dc.port('dn_webapp_https'))

    def configure_client(self):
        self.configure_hdfs_base(*self._remote("namenode"))

    def configure_hdfs_base(self, host, port):
        dc = self.hadoop_base.dist_config
        core_site = dc.path('hadoop_conf') / 'core-site.xml'
        with utils.xmlpropmap_edit_in_place(core_site) as props:
            if host and port:
                props['fs.defaultFS'] = "hdfs://{host}:{port}".format(host=host, port=port)
            props['hadoop.proxyuser.hue.hosts'] = "*"
            props['hadoop.proxyuser.hue.groups'] = "*"
            props['hadoop.proxyuser.oozie.groups'] = '*'
            props['hadoop.proxyuser.oozie.hosts'] = '*'
            lzo_installed = unitdata.kv().get('hadoop.lzo.installed')
            lzo_enabled = hookenv.config().get('compression') == 'lzo'
            if lzo_installed and lzo_enabled:
                props['io.compression.codecs'] = ('com.hadoop.compression.lzo.LzoCodec, '
                                                  'com.hadoop.compression.lzo.LzopCodec')
                props['io.compression.codec.lzo.class'] = 'com.hadoop.compression.lzo.LzoCodec'
        hdfs_site = dc.path('hadoop_conf') / 'hdfs-site.xml'
        with utils.xmlpropmap_edit_in_place(hdfs_site) as props:
            props['dfs.webhdfs.enabled'] = "true"
            props['dfs.namenode.name.dir'] = dc.path('hdfs_dir_base') / 'cache/hadoop/dfs/name'
            props['dfs.datanode.data.dir'] = dc.path('hdfs_dir_base') / 'cache/hadoop/dfs/name'
            props['dfs.permissions'] = 'false'  # TODO - secure this hadoop installation!

    def format_namenode(self):
        if unitdata.kv().get('hdfs.namenode.formatted'):
            return
        self.stop_namenode()
        # Run without prompting; this will fail if the namenode has already
        # been formatted -- we do not want to reformat existing data!
        self._hdfs('namenode', '-format', '-noninteractive')
        unitdata.kv().set('hdfs.namenode.formatted', True)
        unitdata.kv().flush(True)

    def create_hdfs_dirs(self):
        if unitdata.kv().get('hdfs.namenode.dirs.created'):
            return
        self._hdfs('dfs', '-mkdir', '-p', '/tmp/hadoop/mapred/staging')
        self._hdfs('dfs', '-chmod', '-R', '1777', '/tmp/hadoop/mapred/staging')
        self._hdfs('dfs', '-mkdir', '-p', '/tmp/hadoop-yarn/staging')
        self._hdfs('dfs', '-chmod', '-R', '1777', '/tmp/hadoop-yarn')
        self._hdfs('dfs', '-mkdir', '-p', '/user/ubuntu')
        self._hdfs('dfs', '-chown', '-R', 'ubuntu', '/user/ubuntu')
        # for JobHistory
        self._hdfs('dfs', '-mkdir', '-p', '/mr-history/tmp')
        self._hdfs('dfs', '-chmod', '-R', '1777', '/mr-history/tmp')
        self._hdfs('dfs', '-mkdir', '-p', '/mr-history/done')
        self._hdfs('dfs', '-chmod', '-R', '1777', '/mr-history/done')
        self._hdfs('dfs', '-chown', '-R', 'mapred:hdfs', '/mr-history')
        self._hdfs('dfs', '-mkdir', '-p', '/app-logs')
        self._hdfs('dfs', '-chmod', '-R', '1777', '/app-logs')
        self._hdfs('dfs', '-chown', 'yarn', '/app-logs')
        unitdata.kv().set('hdfs.namenode.dirs.created', True)
        unitdata.kv().flush(True)

    def register_slaves(self, slaves=None):
        if not slaves:  # FIXME hack-around until transition to layers is complete
            slaves = helpers.all_ready_units('datanode')
            slaves = [data['hostname'] for slave, data in slaves]
        self.hadoop_base.register_slaves(slaves)
        if utils.jps('NameNode'):
            self.hadoop_base.run('hdfs', 'bin/hdfs', 'dfsadmin', '-refreshNodes')

    def _hadoop_daemon(self, command, service):
        self.hadoop_base.run('hdfs', 'sbin/hadoop-daemon.sh',
                             '--config',
                             self.hadoop_base.dist_config.path('hadoop_conf'),
                             command, service)

    def _hdfs(self, command, *args):
        self.hadoop_base.run('hdfs', 'bin/hdfs', command, *args)


class YARN(object):
    def __init__(self, hadoop_base):
        self.hadoop_base = hadoop_base

    def stop_resourcemanager(self):
        self._yarn_daemon('stop', 'resourcemanager')

    def start_resourcemanager(self):
        if not utils.jps('ResourceManager'):
            self._yarn_daemon('start', 'resourcemanager')

    def stop_jobhistory(self):
        self._jobhistory_daemon('stop', 'historyserver')

    def start_jobhistory(self):
        if not utils.jps('JobHistoryServer'):
            self._jobhistory_daemon('start', 'historyserver')

    def stop_nodemanager(self):
        self._yarn_daemon('stop', 'nodemanager')

    def start_nodemanager(self):
        if not utils.jps('NodeManager'):
            self._yarn_daemon('start', 'nodemanager')

    def _remote(self, relation):
        """
        Return the hostname of the unit on the other end of the given
        relation (derived from that unit's name) and the port used to talk
        to that unit.
        :param str relation: Name of the relation, e.g. "resourcemanager" or "nodemanager"
        """
        # FIXME delete when transition to layers is complete
        unit, data = helpers.any_ready_unit(relation)
        if not unit:
            return None, None
        host = unit.replace('/', '-')
        port = data['port']
        history_http = data['historyserver-http']
        history_ipc = data['historyserver-ipc']
        return host, port, history_http, history_ipc

    def _local(self):
        """
        Return the local hostname (which we derive from our unit name),
        and resourcemanager port from our dist.yaml
        """
        host = hookenv.local_unit().replace('/', '-')
        port = self.hadoop_base.dist_config.port('resourcemanager')
        history_http = self.hadoop_base.dist_config.port('jh_webapp_http')
        history_ipc = self.hadoop_base.dist_config.port('jobhistory')
        return host, port, history_http, history_ipc

    def configure_resourcemanager(self):
        self.configure_yarn_base(*self._local())
        dc = self.hadoop_base.dist_config
        yarn_site = dc.path('hadoop_conf') / 'yarn-site.xml'
        with utils.xmlpropmap_edit_in_place(yarn_site) as props:
            # 0.0.0.0 will listen on all interfaces, which is what we want on the server
            props['yarn.resourcemanager.webapp.address'] = '0.0.0.0:{}'.format(dc.port('rm_webapp_http'))
            # TODO: support SSL
            # props['yarn.resourcemanager.webapp.https.address'] = '0.0.0.0:{}'.format(dc.port('rm_webapp_https'))

    def configure_jobhistory(self):
        self.configure_yarn_base(*self._local())
        dc = self.hadoop_base.dist_config
        mapred_site = dc.path('hadoop_conf') / 'mapred-site.xml'
        with utils.xmlpropmap_edit_in_place(mapred_site) as props:
            # 0.0.0.0 will listen on all interfaces, which is what we want on the server
            props["mapreduce.jobhistory.address"] = "0.0.0.0:{}".format(dc.port('jobhistory'))
            props["mapreduce.jobhistory.webapp.address"] = "0.0.0.0:{}".format(dc.port('jh_webapp_http'))

    def configure_nodemanager(self, host=None, port=None, history_http=None, history_ipc=None):
        if not all([host, port, history_http, history_ipc]):
            # FIXME hack-around until transition to layers is complete
            host, port, history_http, history_ipc = self._remote("nodemanager")
        self.configure_yarn_base(host, port, history_http, history_ipc)

    def configure_client(self, host=None, port=None, history_http=None, history_ipc=None):
        if not all([host, port, history_http, history_ipc]):
            # FIXME hack-around until transition to layers is complete
            host, port, history_http, history_ipc = self._remote("resourcemanager")
        self.configure_yarn_base(host, port, history_http, history_ipc)

    def configure_yarn_base(self, host, port, history_http, history_ipc):
        dc = self.hadoop_base.dist_config
        yarn_site = dc.path('hadoop_conf') / 'yarn-site.xml'
        with utils.xmlpropmap_edit_in_place(yarn_site) as props:
            props['yarn.nodemanager.aux-services'] = 'mapreduce_shuffle'
            props['yarn.nodemanager.vmem-check-enabled'] = 'false'
            if host:
                props['yarn.resourcemanager.hostname'] = '{}'.format(host)
                props['yarn.resourcemanager.address'] = '{}:{}'.format(host, port)
                props["yarn.log.server.url"] = "{}:{}/jobhistory/logs/".format(host, history_http)
        mapred_site = dc.path('hadoop_conf') / 'mapred-site.xml'
        with utils.xmlpropmap_edit_in_place(mapred_site) as props:
            if host and history_ipc:
                props["mapreduce.jobhistory.address"] = "{}:{}".format(host, history_ipc)
            props["mapreduce.framework.name"] = 'yarn'

    def install_demo(self):
        if unitdata.kv().get('yarn.client.demo.installed'):
            return
        # Copy our demo (TeraSort) to the target location and set mode/owner
        demo_source = 'scripts/terasort.sh'
        demo_target = '/home/ubuntu/terasort.sh'

        Path(demo_source).copy(demo_target)
        Path(demo_target).chmod(0o755)
        Path(demo_target).chown('ubuntu', 'hadoop')
        unitdata.kv().set('yarn.client.demo.installed', True)
        unitdata.kv().flush(True)

    def register_slaves(self, slaves=None):
        if not slaves:  # FIXME hack-around until transition to layers is complete
            slaves = helpers.all_ready_units('nodemanager')
            slaves = [data['hostname'] for slave, data in slaves]
        self.hadoop_base.register_slaves(slaves)
        if utils.jps('ResourceManager'):
            self.hadoop_base.run('mapred', 'bin/yarn', 'rmadmin', '-refreshNodes')

    def _yarn_daemon(self, command, service):
        self.hadoop_base.run('yarn', 'sbin/yarn-daemon.sh',
                             '--config',
                             self.hadoop_base.dist_config.path('hadoop_conf'),
                             command, service)

    def _jobhistory_daemon(self, command, service):
        # TODO refactor job history to separate class
        self.hadoop_base.run('mapred', 'sbin/mr-jobhistory-daemon.sh',
                             '--config',
                             self.hadoop_base.dist_config.path('hadoop_conf'),
                             command, service)
