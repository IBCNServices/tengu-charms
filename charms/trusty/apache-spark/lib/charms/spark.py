from glob import glob
from path import Path
from subprocess import CalledProcessError

import jujuresources
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from jujubigdata import utils


# Main Spark class for callbacks
class Spark(object):
    def __init__(self, dist_config):
        self.dist_config = dist_config
        self.resources = {
            'spark': 'spark-%s' % utils.cpu_arch(),
        }
        self.verify_resources = utils.verify_resources(*self.resources.values())

    def is_installed(self):
        return unitdata.kv().get('spark.installed')

    def install(self, force=False):
        if not force and self.is_installed():
            return
        self.dist_config.add_dirs()
        self.dist_config.add_packages()
        jujuresources.install(self.resources['spark'],
                              destination=self.dist_config.path('spark'),
                              skip_top_level=True)
        self.install_demo()

        unitdata.kv().set('spark.installed', True)
        unitdata.kv().flush(True)

    def install_demo(self):
        '''
        Install sparkpi.sh to /home/ubuntu (executes SparkPI example app)
        '''
        demo_source = 'scripts/sparkpi.sh'
        demo_target = '/home/ubuntu/sparkpi.sh'
        Path(demo_source).copy(demo_target)
        Path(demo_target).chmod(0o755)
        Path(demo_target).chown('ubuntu', 'hadoop')

    def setup_spark_config(self):
        '''
        copy the default configuration files to spark_conf property
        defined in dist.yaml
        '''
        default_conf = self.dist_config.path('spark') / 'conf'
        spark_conf = self.dist_config.path('spark_conf')
        spark_conf.rmtree_p()
        default_conf.copytree(spark_conf)
        # Now remove the conf included in the tarball and symlink our real conf
        default_conf.rmtree_p()
        spark_conf.symlink(default_conf)

        spark_env = self.dist_config.path('spark_conf') / 'spark-env.sh'
        if not spark_env.exists():
            (self.dist_config.path('spark_conf') / 'spark-env.sh.template').copy(spark_env)
        spark_default = self.dist_config.path('spark_conf') / 'spark-defaults.conf'
        if not spark_default.exists():
            (self.dist_config.path('spark_conf') / 'spark-defaults.conf.template').copy(spark_default)
        spark_log4j = self.dist_config.path('spark_conf') / 'log4j.properties'
        if not spark_log4j.exists():
            (self.dist_config.path('spark_conf') / 'log4j.properties.template').copy(spark_log4j)
        utils.re_edit_in_place(spark_log4j, {
            r'log4j.rootCategory=INFO, console': 'log4j.rootCategory=ERROR, console',
        })

        # create hdfs storage space
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p', '/user/ubuntu/directory')
        utils.run_as('hdfs', 'hdfs', 'dfs', '-chown', '-R', 'ubuntu:hadoop', '/user/ubuntu/directory')

    def configure(self):
        '''
        Configure spark environment for all users
        '''
        spark_home = self.dist_config.path('spark')
        spark_bin = spark_home / 'bin'

        # put our jar in hdfs
        spark_assembly_jar = glob('{}/lib/spark-assembly-*.jar'.format(spark_home))[0]
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p', '/user/ubuntu/share/lib')
        try:
            utils.run_as('hdfs', 'hdfs', 'dfs', '-put', spark_assembly_jar, '/user/ubuntu/share/lib/spark-assembly.jar')
        except CalledProcessError:
            print ("File exists")

        # update environment variables
        with utils.environment_edit_in_place('/etc/environment') as env:
            if spark_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], spark_bin])
            env['MASTER'] = hookenv.config('spark_execution_mode')
            env['PYSPARK_DRIVER_PYTHON'] = "ipython"
            env['SPARK_CONF_DIR'] = self.dist_config.path('spark_conf')
            env['SPARK_HOME'] = spark_home
            env['SPARK_JAR'] = "hdfs:///user/ubuntu/share/lib/spark-assembly.jar"

        # update spark config
        spark_conf = self.dist_config.path('spark_conf') / 'spark-defaults.conf'
        utils.re_edit_in_place(spark_conf, {
            r'.*spark.eventLog.enabled *.*': 'spark.eventLog.enabled    true',
            r'.*spark.eventLog.dir *.*': 'spark.eventLog.dir    hdfs:///user/ubuntu/directory',
            })

    def open_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.close_port(port)

    def start(self):
        spark_home = self.dist_config.path('spark')
        if utils.jps("HistoryServer"):
            self.stop()
        utils.run_as('ubuntu', '{}/sbin/start-history-server.sh'.format(spark_home), 'hdfs:///user/ubuntu/directory')

    def stop(self):
        if not unitdata.kv().get('spark.installed', False):
            return
        spark_home = self.dist_config.path('spark')
        utils.run_as('ubuntu', '{}/sbin/stop-history-server.sh'.format(spark_home))
