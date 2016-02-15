# python3
#!/usr/bin/env python
# pylint: disable=c0111,c0103,c0301
import base64
import os
from os.path import expanduser
import shutil
import tempfile
import pwd
import grp
import subprocess


# Charm pip dependencies
from charmhelpers import fetch
from charmhelpers.core import templating, hookenv, host
from charms.reactive import hook, when, when_not, set_state, remove_state

# non-standard pip dependencies
import yaml


TENGU_DIR = '/opt/tengu'
GLOBAL_CONF_PATH = TENGU_DIR + '/etc/global-conf.yaml'
KEY_PATH = TENGU_DIR + '/etc/jfed_cert.crt'
S4_CERT_PATH = TENGU_DIR + '/etc/s4_cert.pem.xml'
USER = 'ubuntu'
HOME = '/home/{}'.format(USER)
SSH_DIR = HOME + '/.ssh'


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
    with open(expanduser(GLOBAL_CONF_PATH), 'w') as config_file:
        config_file.write(yaml.dump(content, default_flow_style=False))
    set_state('tengu.configured')
    chownr(os.path.dirname(GLOBAL_CONF_PATH), USER, USER)


@when('tengu.installed')
@when_not('rest2jfed.available')
def set_blocked():
    hookenv.status_set('blocked', 'Waiting for connection to rest2jfed')


@when('tengu.installed', 'tengu.configured', 'tengu.repo.available', 'juju.repo.available', 'rest2jfed.configured')
def create_environment(*arg):
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
        subprocess.check_call(['su', '-', USER, '-c', '{}/scripts/tengu.py create --bundle {} {}'.format(TENGU_DIR, bundle_path, hostname[2:])])


@when('rest2jfed.available')
@when_not('rest2jfed.configured')
def setup_rest2jfed(rest2jfed):
    hostname = rest2jfed.services()[0]['hosts'][0]['hostname']
    port = rest2jfed.services()[0]['hosts'][0]['port']
    with open(GLOBAL_CONF_PATH, 'r') as infile:
        content = yaml.load(infile)
    content['rest2jfed-hostname'] = str(hostname)
    content['rest2jfed-port'] = str(port)
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
        context={'tengu_dir' : TENGU_DIR}
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
    ssh_pub_keypath = expanduser("{}/id_rsa.pub".format(keysdir))
    ssh_priv_keypath = expanduser("{}/id_rsa".format(keysdir))
    authorized_keys = expanduser("{}/authorized_keys".format(keysdir))
    if not os.path.isfile(ssh_pub_keypath):
        subprocess.check_call(['ssh-keygen', '-t', 'rsa', '-N', '""', '-f', ssh_priv_keypath])
        with open(ssh_pub_keypath, 'r') as pubkeyfile:
            pubkey = pubkeyfile.read().rstrip()
        with open(authorized_keys, 'a') as auth_keyfile:
            auth_keyfile.write(pubkey + "\n")
        chownr(keysdir, user, group)
    with open(ssh_pub_keypath, 'r') as pubkeyfile:
        return pubkeyfile.read().rstrip()
