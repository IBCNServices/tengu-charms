from glob import glob
from path import Path
from subprocess import CalledProcessError

import jujuresources
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers.core import unitdata
from charmhelpers.fetch.archiveurl import ArchiveUrlFetchHandler
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
        jujuresources.install(self.resources['spark'],
                              destination=self.dist_config.path('spark'),
                              skip_top_level=True)

        # allow ubuntu user to ssh to itself so spark can ssh to its worker
        # in local/standalone modes
        utils.install_ssh_key('ubuntu', utils.get_ssh_key('ubuntu'))

        # put the spark jar in hdfs
        spark_assembly_jar = glob('{}/lib/spark-assembly-*.jar'.format(
                                  self.dist_config.path('spark')))[0]
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p',
                     '/user/ubuntu/share/lib')
        try:
            utils.run_as('hdfs', 'hdfs', 'dfs', '-put', spark_assembly_jar,
                         '/user/ubuntu/share/lib/spark-assembly.jar')
        except CalledProcessError:
            print ("File exists")

        # create hdfs storage space for history server
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p',
                     '/user/ubuntu/directory')
        utils.run_as('hdfs', 'hdfs', 'dfs', '-chown', '-R', 'ubuntu:hadoop',
                     '/user/ubuntu/directory')

        # create hdfs storage space for spark-bench
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p',
                     '/user/ubuntu/spark-bench')
        utils.run_as('hdfs', 'hdfs', 'dfs', '-chown', '-R', 'ubuntu:hadoop',
                     '/user/ubuntu/spark-bench')

        unitdata.kv().set('spark.installed', True)
        unitdata.kv().flush(True)

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

    def install_demo(self):
        '''
        Install sparkpi.sh to /home/ubuntu (executes SparkPI example app)
        '''
        demo_source = 'scripts/sparkpi.sh'
        demo_target = '/home/ubuntu/sparkpi.sh'
        Path(demo_source).copy(demo_target)
        Path(demo_target).chmod(0o755)
        Path(demo_target).chown('ubuntu', 'hadoop')

    def is_spark_local(self):
        # spark is local if our execution mode is 'local*' or 'standalone'
        mode = hookenv.config()['spark_execution_mode']
        if mode.startswith('local'):
            return True
        else:
            return False

    # translate our execution_mode into the appropriate --master value
    def get_master(self):
        mode = hookenv.config()['spark_execution_mode']
        master = None
        if mode.startswith('local') or mode == 'yarn-cluster':
            master = mode
        elif mode == 'standalone':
            local_ip = utils.resolve_private_address(hookenv.unit_private_ip())
            master = 'spark://{}:7077'.format(local_ip)
        elif mode.startswith('yarn'):
            master = 'yarn-client'
        return master

    def configure(self):
        '''
        Configure spark environment for all users
        '''
        spark_home = self.dist_config.path('spark')
        spark_bin = spark_home / 'bin'

        # handle tuning options that may be set as percentages
        driver_mem = '1g'
        req_driver_mem = hookenv.config()['driver_memory']
        executor_mem = '1g'
        req_executor_mem = hookenv.config()['executor_memory']
        if req_driver_mem.endswith('%'):
            if self.is_spark_local():
                mem_mb = host.get_total_ram() / 1024 / 1024
                req_percentage = float(req_driver_mem.strip('%')) / 100
                driver_mem = str(int(mem_mb * req_percentage)) + 'm'
            else:
                hookenv.log("driver_memory percentage in non-local mode. Using 1g default.",
                            level=None)
        else:
            driver_mem = req_driver_mem

        if req_executor_mem.endswith('%'):
            if self.is_spark_local():
                mem_mb = host.get_total_ram() / 1024 / 1024
                req_percentage = float(req_executor_mem.strip('%')) / 100
                executor_mem = str(int(mem_mb * req_percentage)) + 'm'
            else:
                hookenv.log("executor_memory percentage in non-local mode. Using 1g default.",
                            level=None)
        else:
            executor_mem = req_executor_mem

        # update environment variables
        with utils.environment_edit_in_place('/etc/environment') as env:
            if spark_bin not in env['PATH']:
                env['PATH'] = ':'.join([env['PATH'], spark_bin])
            env['MASTER'] = self.get_master()
            env['PYSPARK_DRIVER_PYTHON'] = "ipython"
            env['SPARK_CONF_DIR'] = self.dist_config.path('spark_conf')
            env['SPARK_DRIVER_MEMORY'] = driver_mem
            env['SPARK_EXECUTOR_MEMORY'] = executor_mem
            env['SPARK_HOME'] = spark_home
            env['SPARK_JAR'] = "hdfs:///user/ubuntu/share/lib/spark-assembly.jar"

        # update spark config
        spark_conf = self.dist_config.path('spark_conf') / 'spark-defaults.conf'
        utils.re_edit_in_place(spark_conf, {
            r'.*spark.master *.*': 'spark.master {}'.format(self.get_master()),
            r'.*spark.eventLog.enabled *.*': 'spark.eventLog.enabled true',
            r'.*spark.eventLog.dir *.*': 'spark.eventLog.dir hdfs:///user/ubuntu/directory',
            })
        spark_env = self.dist_config.path('spark_conf') / 'spark-env.sh'
        local_ip = utils.resolve_private_address(hookenv.unit_private_ip())
        utils.re_edit_in_place(spark_env, {
            r'.*SPARK_DRIVER_MEMORY.*': 'SPARK_DRIVER_MEMORY={}'.format(driver_mem),
            r'.*SPARK_EXECUTOR_MEMORY.*': 'SPARK_EXECUTOR_MEMORY={}'.format(executor_mem),
            r'.*SPARK_LOG_DIR.*': 'SPARK_LOG_DIR={}'.format(self.dist_config.path('spark_logs')),
            r'.*SPARK_MASTER_IP.*': 'SPARK_MASTER_IP={}'.format(local_ip),
            r'.*SPARK_WORKER_DIR.*': 'SPARK_WORKER_DIR={}'.format(self.dist_config.path('spark_work')),
            })

        # manage SparkBench
        install_sb = hookenv.config()['spark_bench_enabled']
        sb_dir = '/home/ubuntu/spark-bench'
        if install_sb:
            if not unitdata.kv().get('spark_bench.installed', False):
                if utils.cpu_arch() == 'ppc64le':
                    sb_url = hookenv.config()['spark_bench_ppc64le']
                else:
                    # TODO: may need more arch cases (go with x86 sb for now)
                    sb_url = hookenv.config()['spark_bench_x86_64']

                Path(sb_dir).rmtree_p()
                au = ArchiveUrlFetchHandler()
                au.install(sb_url, '/home/ubuntu')

                # #####
                # Handle glob if we use a .tgz that doesn't expand to sb_dir
                # sb_archive_dir = glob('/home/ubuntu/spark-bench-*')[0]
                # SparkBench expects to live in ~/spark-bench, so put it there
                # Path(sb_archive_dir).rename(sb_dir)
                # #####

                # comment out mem tunings (let them come from /etc/environment)
                sb_env = Path(sb_dir) / 'conf/env.sh'
                utils.re_edit_in_place(sb_env, {
                    r'^SPARK_DRIVER_MEMORY.*': '# SPARK_DRIVER_MEMORY (use value from environment)',
                    r'^SPARK_EXECUTOR_MEMORY.*': '# SPARK_EXECUTOR_MEMORY (use value from environment)',
                    })

                unitdata.kv().set('spark_bench.installed', True)
                unitdata.kv().flush(True)
        else:
            Path(sb_dir).rmtree_p()
            unitdata.kv().set('spark_bench.installed', False)
            unitdata.kv().flush(True)

    def open_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.close_port(port)

    def start(self):
        spark_home = self.dist_config.path('spark')
        # stop services (if they're running) to pick up any config change
        self.stop()
        # always start the history server, start master/worker if we're standalone
        utils.run_as('ubuntu', '{}/sbin/start-history-server.sh'.format(spark_home), 'hdfs:///user/ubuntu/directory')
        if hookenv.config()['spark_execution_mode'] == 'standalone':
            utils.run_as('ubuntu', '{}/sbin/start-master.sh'.format(spark_home))
            utils.run_as('ubuntu', '{}/sbin/start-slave.sh'.format(spark_home), self.get_master())

    def stop(self):
        if not unitdata.kv().get('spark.installed', False):
            return
        spark_home = self.dist_config.path('spark')
        # Only stop services if they're running
        if utils.jps("HistoryServer"):
            utils.run_as('ubuntu', '{}/sbin/stop-history-server.sh'.format(spark_home))
        if utils.jps("Master"):
            utils.run_as('ubuntu', '{}/sbin/stop-master.sh'.format(spark_home))
        if utils.jps("Worker"):
            utils.run_as('ubuntu', '{}/sbin/stop-slave.sh'.format(spark_home))
