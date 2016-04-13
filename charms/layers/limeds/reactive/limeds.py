# python3 pylint: disable=c0111,c0301
import os
import shutil
import subprocess

from charms.apt import add_source, queue_install, install_queued #(dependency will be added by apt layer) pylint: disable=E0401,E0611
from charms.reactive import when, when_not, hook
from charms.reactive import set_state, remove_state
from charmhelpers.core import hookenv, host, templating
from charmhelpers.core.hookenv import open_port


# Fix for issue where $HOME is not /root while running debug-hooks or dhx
os.environ['HOME'] = "/root"


@when('java.installed')
@when_not('limeds.installed')
def install():
    install_limeds()
    restart_limeds()
    set_state('limeds.installed')
    hookenv.status_set('active', 'Ready')


@hook('upgrade-charm')
def upgrade():
    upgrade_limeds()
    set_state('limeds.installed')


@when('limeds.installed', 'mongodb.available')
@when_not('mongodb.configured')
def configure_limeds(mongodb):
    hookenv.status_set('maintenance', 'Setting up LimeDS MongoDB relation')
    configure_limeds_mongodb(mongodb.hostname, mongodb.port)
    restart_limeds()
    set_state('mongodb.configured')
    hookenv.status_set('active', 'Ready & connected to MongoDB')


@when('mongodb.configured')
@when_not('mongodb.available')
def remove_mongodb_configured():
    remove_state('mongodb.configured')


def install_limeds():
    add_source('ppa:cwchien/gradle')
    queue_install(['git', 'gradle'])
    install_queued()
    service_name = hookenv.local_unit().split('/')[0]
    subprocess.check_call(['hostnamectl', 'set-hostname', ''])
    # Make hostname resolvable
    with open('/etc/hosts', 'a') as hosts_file:
        hosts_file.write('127.0.0.1 {}\n'.format(service_name))
    # Add bitbucket host key so git ssh doesn't request to confirm host key
    with open('/root/.ssh/known_hosts', 'a+') as known_hosts_file:
        known_hosts_file.write('bitbucket.org ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAubiN81eDcafrgMeLzaFPsw2kNvEcqTKl/VqLat/MaB33pZy0y3rJZtnqwR2qOOvbwKZYKiEO1O6VqNEBxKvJJelCq0dTXWT5pbO2gDXC6h6QDXCaHo6pOHGPUy+YBaGQRGuSusMEASYiWunYN0vCAI8QaXnWMXNMdFP3jHAJH0eDsoiGnLPBlBp4TNm6rYI74nMzgz3B9IikW4WVK+dc8KZJZWYjAuORU3jc1c/NPskD2ASinf8v3xnfXeukU0sJ5N6m5E8VLjObPEO+mN2t/FZTMZLiFqPWc/ALSqnMnnhwrNi2rbfg/rd/IpL8Le3pSBne8+seeFVBoGqzHM9yXw=\n')
    if os.path.isdir('/opt/limeds'):
        shutil.rmtree('/opt/limeds')
    keypath = '{}/files/id_rsa'.format(hookenv.charm_dir())
    # Fix bug where permissions of charm files are changed
    subprocess.check_call(['chmod', 'go-r', keypath])
    repo = 'git@bitbucket.org:ibcndevs/limeds.git'
    subprocess.check_call([
        # use ssh-agent to use supplied privkey for git ssh connection
        'ssh-agent', 'bash', '-c',
        # remote 'upstream' will point to supplied given repo
        'ssh-add {}; git clone {} -o upstream'.format(keypath, repo)
    ], cwd='/opt/')
    subprocess.check_call([
        'gradle', 'jar', 'export'
    ], cwd='/opt/limeds')
    templating.render(
        source='upstart.conf',
        target='/etc/init/limeds.conf',
        context={
            'description': 'limeds',
            'command': 'cd /opt/limeds/run/ \njava -jar generated/distributions/executable/limeds.jar'
        }
    )


def upgrade_limeds():
    subprocess.check_call([
        'git', 'pull', 'upstream', 'master'
    ], cwd='/opt/limeds')
    restart_limeds()


def restart_limeds():
    host.service_stop('limeds')
    success = host.service_start('limeds')
    success = host.service_start('isc-dhcp-server')
    if not success:
        print("starting limeds failed!")
        exit(1)
    open_port('80') # LimeDS running on localhost:80/system/console


def configure_limeds_mongodb(hostname, port):
    templating.render(
        source='org.ibcn.limeds.mongodb.MongoStorage.cfg',
        target='/opt/limeds/run/org.ibcn.limeds.mongodb.MongoStorage.cfg',
        context={
            'hostname': hostname,
            'port': port,
            'database_name': 'test'
        }
    )
