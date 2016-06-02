# python3 pylint: disable=c0111,c0301
# Copyright (C) 2016  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import pwd
import grp
import os
import shutil
import subprocess

from charms.reactive import when, when_not, hook
from charms.reactive import set_state, remove_state
from charmhelpers.core import hookenv, host, templating
from charmhelpers.core.hookenv import open_port, close_port, charm_dir
from charms import apt #(dependency will be added by apt layer) pylint: disable=E0401,E0611

# Fix for issue where $HOME is not /root while running debug-hooks or dhx
os.environ['HOME'] = "/root"

@when_not('rest2kafka.installed')
def install():
    install_rest2kafka()
    set_state('rest2kafka.installed')
    hookenv.status_set('blocked', 'Waiting for relation to Kafka')


@hook('upgrade-charm')
def upgrade():
    upgrade_rest2kafka()
    set_state('rest2kafka.installed')

@when_not('kafka.configured')
def configure_rest2kafka(kafka):
    if kafka.kafkas():
        hookenv.status_set('maintenance', 'Setting up rest2kafka kafka relation')
        configure_rest2kafka_kafka(kafka)
        restart_rest2kafka()
        set_state('kafka.configured')
        hookenv.status_set('active', 'Ready & connected to kafka')

@when('kafka.configured')
@when_not('kafka.joined')
def remove_kafka_configured():
    remove_state('kafka.configured')

def install_rest2kafka():
    apt.add_source('ppa:cwchien/gradle')
    apt.queue_install(['python-pip', 'python-dev'])
    apt.update()
    apt.install_queued()
    subprocess.check_call(['pip2', 'install', 'pykafka', 'flask'])
    # Make hostname resolvable
    service_name = hookenv.local_unit().split('/')[0]
    with open('/etc/hosts', 'a') as hosts_file:
        hosts_file.write('127.0.0.1 {}\n'.format(service_name))
    mergecopytree(charm_dir() + '/files/rest2kafka', "/opt/rest2kafka")
    chownr('/opt/rest2kafka', 'ubuntu', 'ubuntu')
    templating.render(
        source='upstart.conf',
        target='/etc/init/rest2kafka.conf',
        owner='ubuntu',
        group='ubuntu',
        context={
            'user': 'ubuntu',
            'description': 'rest2kafka',
            'command': '/opt/rest2kafka/rest2kafka.py',
            'debug': 'False',
        }
    )


def configure_rest2kafka_kafka(kafka):
    templating.render(
        source='kafka.connect',
        target='/opt/rest2kafka/etc/kafka.connect',
        context={
            'kafkas': kafka.kafkas(),
        }
    )

def upgrade_rest2kafka():
    stop_rest2kafka()
    install_rest2kafka()
    start_rest2kafka()
    hookenv.status_set('active', 'Ready')

def start_rest2kafka():
    success = host.service_start('rest2kafka')
    if not success:
        print("starting rest2kafka failed!")
        exit(1)
    open_port('5000')
    set_state('rest2kafka.started')

def stop_rest2kafka():
    host.service_stop('rest2kafka')
    close_port('5000')
    remove_state('rest2kafka.started')

def restart_rest2kafka():
    stop_rest2kafka()
    start_rest2kafka()


def mergecopytree(src, dst, symlinks=False, ignore=None):
    """"Recursive copy src to dst, mergecopy directory if dst exists.
    OVERWRITES EXISTING FILES!!"""
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if symlinks and os.path.islink(src_item):
            if os.path.lexists(dst_item):
                os.remove(dst_item)
            os.symlink(os.readlink(src_item), dst_item)
        elif os.path.isdir(src_item):
            mergecopytree(src_item, dst_item, symlinks, ignore)
        else:
            shutil.copy2(src_item, dst_item)


def chownr(path, owner, group, follow_links=True):
    uid = pwd.getpwnam(owner).pw_uid
    gid = grp.getgrnam(group).gr_gid
    if follow_links:
        chown = os.chown
    else:
        chown = os.lchown
    chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            full = os.path.join(root, name)
            broken_symlink = os.path.lexists(full) and not os.path.exists(full)
            if not broken_symlink:
                chown(full, uid, gid)
