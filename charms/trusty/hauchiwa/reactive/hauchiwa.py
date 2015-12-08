#!/usr/bin/env python3
# pylint: disable=c0111,c0103
"""hooks"""
from os.path import expanduser
import yaml
import base64
import os
import shutil
import tempfile
import pwd
import grp
import subprocess

from charmhelpers import fetch
from charmhelpers.core import templating, hookenv, host
from charms.reactive import hook, when, when_not, set_state, remove_state


TENGU_DIR = '/opt/tengu'
GLOBAL_CONF_PATH = TENGU_DIR + '/etc/global-conf.yaml'
KEY_PATH = TENGU_DIR + '/etc/jfed_cert.crt'
S4_CERT_PATH = TENGU_DIR + '/etc/s4_cert.pem.xml'
USER = 'ubuntu'
HOME = '/home/{}'.format(USER)



@hook('upgrade-charm')
def upgrade_charm():
    """Upgrade Charm"""
    hookenv.log('Updating tengu-instance-admin')
    install_tengu()


@when('juju.installed')
@when_not('tengu.installed')
def install():
    """Install"""
    hookenv.log('Installing tengu-instance-admin')
    install_tengu()
    set_state('tengu.installed')


@hook('config-changed')
def config_changed():
    """Config changed"""
    conf = hookenv.config()
    with open(S4_CERT_PATH, 'w+') as certfile:
        certfile.write(str(base64.b64decode(conf['emulab-s4-cert'])))
        certfile.truncate()
    with open(GLOBAL_CONF_PATH, 'r') as infile:
        content = yaml.load(infile)
    content['project_name'] = str(conf['emulab-project-name'])
    content['s4_cert_path'] = S4_CERT_PATH
    with open(expanduser(GLOBAL_CONF_PATH), 'w') as config_file:
        config_file.write(yaml.dump(content, default_flow_style=False))


@when('tengu.installed')
@when_not('rest2jfed.available')
def set_blocked():
    hookenv.status_set('blocked', 'Waiting for connection to rest2jfed')


@when('rest2jfed.available')
@when_not('rest2jfed.configured')
def setup_rest2jfed(rest2jfed):
    hostname = rest2jfed.services()[0]['hosts'][0]['hostname']
    port = rest2jfed.services()[0]['hosts'][0]['port']
    with open(GLOBAL_CONF_PATH, 'r') as infile:
        content = yaml.load(infile)
    content['rest2jfed_hostname'] = str(hostname)
    content['rest2jfed_port'] = str(port)
    with open(expanduser(GLOBAL_CONF_PATH), 'w') as config_file:
        config_file.write(yaml.dump(content, default_flow_style=False))
    set_state('rest2jfed.configured')
    hookenv.status_set('active', 'Ready')


@when('rest2jfed.configured')
@when_not('rest2jfed.available')
def remove_rest2jfed():
    remove_state('rest2jfed.configured')


def install_tengu():
    """ Installs tengu management tools """
    packages = ['python-pip']
    fetch.apt_install(fetch.filter_installed_packages(packages))
    subprocess.check_output(['pip', 'install', 'Jinja2', 'Flask', 'pyyaml'])
    # Install Tengu. Existing /etc files don't get overwritten.
    t_dir = None
    if os.path.isdir(TENGU_DIR + '/etc'):
        t_dir = tempfile.mkdtemp()
        mergecopytree(TENGU_DIR + '/etc', t_dir)
        mergecopytree('files/tengu_management', TENGU_DIR)
        mergecopytree(t_dir, TENGU_DIR + '/etc')
    else:
        mergecopytree('files/tengu_management', TENGU_DIR)
        templating.render(
            source='global-conf.yaml',
            target=GLOBAL_CONF_PATH,
            perms=493,
            context={
                's4_cert_path': S4_CERT_PATH,
                'key_path': KEY_PATH
            }
        )
    templating.render(
        source='tengu',
        target='/usr/bin/tengu',
        perms=493,
        context={}
    )
    chownr(TENGU_DIR, USER, USER)
    templating.render(
        source='upstart.conf',
        target='/etc/init/h_api.conf',
        context={}
    )

    # get the name of this service from the unit name
    service_name = hookenv.local_unit().split('/')[0]
    # set it as hostname
    subprocess.check_call(['hostname', 'service_name'])
    # Persist hostname
    with open('/etc/hostname', 'w') as hostname_file:
        hostname_file.write(service_name)
    # Make hostname resolvable
    with open('/etc/hosts', 'a') as hosts_file:
        hosts_file.write('127.0.0.1 {}\n'.format(service_name))
    host.service_restart('h_api')


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
