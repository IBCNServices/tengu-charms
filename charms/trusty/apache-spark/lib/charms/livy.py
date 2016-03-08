#!/usr/bin/python3 pylint:disable=c0103,e0611,c0111,r0201,c0301,e0401
from subprocess import CalledProcessError, call
import os
import jujuresources
from charmhelpers.core import hookenv
from jujubigdata import utils


# Main Livy class for callbacks
class Livy(object):
    def __init__(self, dist_config):
        self.user = 'hue'
        self.dist_config = dist_config
        self.resources = {
            'livy': 'livy-%s' % utils.cpu_arch(),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())


    def install(self):
        self.dist_config.add_users()
        self.dist_config.add_dirs()
        jujuresources.install(self.resources['livy'],
                              destination=self.dist_config.path('livy'),
                              skip_top_level=False)

        livy_bin = self.dist_config.path('livy') / 'bin'
        with utils.environment_edit_in_place('/etc/environment') as env:
            if livy_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], livy_bin])
            # Following classpath comes from `hadoop classpath` and should be fixed
            hadoop_cp = '/etc/hadoop/conf:/usr/lib/hadoop/share/hadoop/common/lib/*:/usr/lib/hadoop/share/hadoop/common/*\
:/usr/lib/hadoop/share/hadoop/hdfs:/usr/lib/hadoop/share/hadoop/hdfs/lib/*\
:/usr/lib/hadoop/share/hadoop/hdfs/*:/usr/lib/hadoop/share/hadoop/yarn/lib/*\
:/usr/lib/hadoop/share/hadoop/yarn/*:/usr/lib/hadoop/share/hadoop/mapreduce/lib/*\
:/usr/lib/hadoop/share/hadoop/mapreduce/*:/usr/lib/hadoop/contrib/capacity-scheduler/*.jar'
            env['CLASSPATH'] = hadoop_cp

        cmd = "chown -R {}:hadoop {}".format(self.user, self.dist_config.path('livy'))
        call(cmd.split())
        cmd = "chown -R {}:hadoop {}".format(self.user, self.dist_config.path('livy_conf'))
        call(cmd.split())

    def configure(self, mode):
        livy_conf = self.dist_config.path('livy') / 'conf/livy-defaults.conf'
        if not livy_conf.exists():
            (self.dist_config.path('livy') / 'conf/livy-defaults.conf.template').copy(livy_conf)
        etc_conf = self.dist_config.path('livy_conf') / 'livy-defaults.conf'
        if not etc_conf.exists():
            livy_conf.symlink(etc_conf)
        if mode == 'yarn-client':
            spark_mode = 'yarn'
        else:
            spark_mode = 'process'
        utils.re_edit_in_place(livy_conf, {
            r'.*livy.server.session.factory =*.*': '  livy.server.session.factory = ' + spark_mode,
            })

    def start(self):
        if not utils.jps("Main"):
            livy_log = self.dist_config.path('livy_logs') / 'livy-server.log'
            livy_home = self.dist_config.path('livy')
            # chdir here because things like zepp tutorial think ZEPPELIN_HOME
            # is wherever the daemon was started from.
            os.chdir(livy_home)
            #utils.run_as(self.user, './bin/livy-server', '2>&1', livy_log, '&')
            #utils.run_as(self.user, './bin/livy-server', '&')
            os.system("su {} -c \"./bin/livy-server 2>&1 > {} &\"".format(self.user, livy_log))

    def stop(self):
        try:
            utils.run_as(self.user, 'pkill', '-f', 'livy')
        except CalledProcessError as error:
            msg = str(error.output), str(error.returncode)
            hookenv.log("Error stopping livy: " + str(msg))

    def open_ports(self):
        for port in self.dist_config.exposed_ports('livy'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('livy'):
            hookenv.close_port(port)
