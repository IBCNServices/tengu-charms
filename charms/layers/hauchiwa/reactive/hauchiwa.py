# python3
# !/usr/bin/env python
# pylint: disable=c0111,c0103,c0301
import base64
import os
from os.path import expanduser
import shutil
import tempfile
import pwd
import grp
import subprocess
#import re

# Charm pip dependencies
from charmhelpers import fetch
from charmhelpers.core import templating, hookenv, host
from charmhelpers.core.hookenv import open_port, config
from charms.reactive import hook, when, when_all, when_not, set_state, remove_state, when_file_changed

# non-standard pip dependencies
import yaml

TENGU_DIR = '/opt/tengu'
GLOBAL_CONF_PATH = TENGU_DIR + '/etc/global-conf.yaml'
KEY_PATH = TENGU_DIR + '/etc/jfed_cert.crt'
S4_CERT_PATH = TENGU_DIR + '/etc/s4_cert.pem.xml'
USER = config()['user']
FLAVOR = config()['hauchiwa-flavor']
HOME = expanduser('~{}'.format(USER))
SSH_DIR = HOME + '/.ssh'


@when('hauchiwa-port-forward.available')
def conf_pf(port_forward):
    port_forward.configure()


@when_all('hauchiwa-port-forward.ready', 'tengu.repo.available', 'juju.repo.available', 'hauchiwa.provider.configured')
def show_pf(port_forward):
    msg = 'Ready pf:"'
    for forward in port_forward.forwards:
        msg += '{}:{}->{} '.format(forward['public_ip'], forward['public_port'], forward['private_port'])
    msg += '"'
    hookenv.status_set('active', msg)


@when('juju.repo.available')
@when_not('tengu.repo.available')
def downloadbigfiles():
    subprocess.check_call(['su', '-', USER, '-c', '{}/scripts/tengu.py downloadbigfiles'.format(TENGU_DIR)])
    set_state('tengu.repo.available')


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
    open_port('22')


@hook('config-changed')
def config_changed():
    """Config changed"""
    conf = hookenv.config()
    with open(S4_CERT_PATH, 'wb+') as certfile:
        certfile.write(base64.b64decode(conf['emulab-s4-cert']))
        certfile.truncate()
    with open(GLOBAL_CONF_PATH, 'r') as infile:
        content = yaml.load(infile)
    content['project-name'] = str(conf['emulab-project-name'])
    content['s4-cert-path'] = S4_CERT_PATH
    content['pubkey'] = get_or_create_ssh_key(SSH_DIR, USER, USER)
    with open(GLOBAL_CONF_PATH, 'w') as config_file:
        config_file.write(yaml.dump(content, default_flow_style=False))
    chownr(os.path.dirname(GLOBAL_CONF_PATH), USER, USER)
    set_state('tengu.configured')


@when('tengu.installed')
@when_not('rest2jfed.available')
def set_blocked():
    if FLAVOR == 'rest2jfed':
        hookenv.status_set('blocked', 'Waiting for connection to rest2jfed')
    elif FLAVOR == 'ssh' or FLAVOR == 'tokin':
        set_state('hauchiwa.provider.configured')
        hookenv.status_set('active', 'Ready')
    else:
        hookenv.status_set('blocked', 'Hauchiwa flavor {} not recognized'.format(FLAVOR))


@when('tengu.configured', 'tengu.repo.available', 'juju.repo.available',
      'hauchiwa.provider.configured')
@when_not('bundle.deployed')
def create_environment(*arg):  # pylint:disable=w0613
    conf = hookenv.config()
    bundle = conf.get('bundle')
    if bundle:
        bundle_dir = tempfile.mkdtemp()
        bundle_path = bundle_dir + '/bundle.yaml'
        with open(bundle_path, 'w+') as bundle_file:
            bundle = base64.b64decode(bundle).decode('utf8')
            bundle_file.write(bundle)
        chownr(bundle_dir, USER, USER)
        hostname = subprocess.getoutput(['hostname'])
        subprocess.check_call(['su', '-', USER, '-c',
                               '{}/scripts/tengu.py create --bundle {} {}'.format(TENGU_DIR, bundle_path,
                                                                                  hostname[2:])])
    set_state('bundle.deployed')


@when('rest2jfed.available')
@when_not('rest2jfed.configured')
def setup_rest2jfed(rest2jfed):
    hostname = rest2jfed.services()[0]['hosts'][0]['hostname']
    port = rest2jfed.services()[0]['hosts'][0]['port']
    with open(GLOBAL_CONF_PATH, 'r') as infile:
        content = yaml.load(infile)
    content['rest2jfed-hostname'] = str(hostname)
    content['rest2jfed-port'] = str(port)
    with open(GLOBAL_CONF_PATH, 'w') as config_file:
        config_file.write(yaml.dump(content, default_flow_style=False))
    set_state('rest2jfed.configured')
    set_state('hauchiwa.provider.configured')


@when('rest2jfed.configured')
@when_not('rest2jfed.available')
def remove_rest2jfed():
    remove_state('rest2jfed.configured')


def install_tengu():
    """ Installs tengu management tools """
    packages = ['python-pip', 'tree']
    fetch.apt_install(fetch.filter_installed_packages(packages))
    subprocess.check_output(['pip2', 'install', 'Jinja2', 'Flask', 'pyyaml', 'click', 'python-dateutil'])
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
        context={'tengu_dir': TENGU_DIR}
    )
    chownr(TENGU_DIR, USER, USER)
    templating.render(
        source='upstart.conf',
        target='/etc/init/h_api.conf',
        context={
            'tengu_dir': TENGU_DIR,
            'user': USER
        }
    )

    # get the name of this service from the unit name
    service_name = hookenv.local_unit().split('/')[0]
    # set service_name as hostname
    subprocess.check_call(['hostnamectl', 'set-hostname', service_name])
    # Make hostname resolvable
    with open('/etc/hosts', 'a') as hosts_file:
        hosts_file.write('127.0.0.1 {}\n'.format(service_name))
    host.service_restart('h_api')
    open_port('5000')
    set_state('h_api.started')


# Service will restart even if files change outside of Juju.
# `update-status` hook will run periodically checking the hash of those files.
@when_file_changed(
    '/etc/init/h_api.conf',
    '/opt/tengu/scripts/h_api.py',
    '/opt/tengu/scripts/jujuhelpers.py')
@when('h_api.started')
def restart():
    host.service_restart('h_api')
    open_port('5000')


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


def get_or_create_ssh_key(keysdir, user, group):
    """ Gets ssh public key. Creates one if it doesn't exist yet. """
    if not os.path.isdir(keysdir):
        os.makedirs(keysdir)
    ssh_pub_keypath = "{}/id_rsa.pub".format(keysdir)
    ssh_priv_keypath = "{}/id_rsa".format(keysdir)
    authorized_keys = "{}/authorized_keys".format(keysdir)
    if not os.path.isfile(ssh_pub_keypath):
        subprocess.check_call(['ssh-keygen', '-t', 'rsa', '-N', '', '-f', ssh_priv_keypath])
        with open(ssh_pub_keypath, 'r') as pubkeyfile:
            pubkey = pubkeyfile.read().rstrip()
        with open(authorized_keys, 'a') as auth_keyfile:
            auth_keyfile.write(pubkey + "\n")
        chownr(keysdir, user, group)
    with open(ssh_pub_keypath, 'r') as pubkeyfile:
        return pubkeyfile.read().rstrip()
