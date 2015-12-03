import os
from os.path import expanduser
import subprocess
import pwd
import grp
import yaml
from base64 import b64decode, b64encode
from subprocess import CalledProcessError, check_output, STDOUT

from charmhelpers import fetch
from charmhelpers.core import hookenv
from charmhelpers.core import templating

from charms import reactive
from charms.reactive import hook

USER = 'ubuntu'
HOME = '/home/{}'.format(USER)


@hook('install')
def install():
    install_packages()
    if not os.path.isfile("{}/.juju/environments.yaml".format(HOME)):
        configure_environments()
    reactive.set_state('juju.installed')


@hook('upgrade-charm')
def upgrade():
    install()
    reactive.set_state('juju.upgraded')


@hook('config-changed')
def config_changed():
    config = hookenv.config()
    git_url = config.get('charm-repo-source')
    if git_url:
        get_and_configure_charm_repo(git_url)
    if config.get('environment-name'):
        import_environment(config)
    reactive.set_state('juju.config-changed')


def install_packages():
    hookenv.status_set('maintenance', 'Installing packages')
    fetch.add_source('ppa:juju/stable')
    fetch.apt_update()
    packages = ['juju', 'juju-core', 'juju-deployer', 'git', 'python-yaml']
    fetch.apt_install(fetch.filter_installed_packages(packages))


def get_and_configure_charm_repo(git_url):
    hookenv.status_set('maintenance', 'Configuring Charm Repo')
    repo_name = git_url.rstrip('.git').split('/')[-1]
    repo_path = '/opt/{}'.format(repo_name)
    if not os.path.isdir(repo_path):
        subprocess.check_call(['git', 'clone', git_url], cwd='/opt/')
        templating.render(
            source='juju.sh',
            target='/etc/profile.d/juju.sh',
            context={
                'charm_repo_path': '{0}/charms'.format(repo_path)
            }
        )
        chownr(repo_path, USER, USER)


def configure_environments():
    hookenv.status_set('maintenance', 'Initializing environment')
    check_output(['su',
                  '-l', USER,
                  '-c', 'juju generate-config'], stderr=STDOUT)
    if not os.path.isdir('{}/.juju/environments'.format(HOME)):
        os.makedirs('{}/.juju/environments'.format(HOME))
    if not os.path.isdir('{}/.juju/ssh'.format(HOME)):
        os.makedirs('{}/.juju/ssh'.format(HOME))
    templating.render(
        source='environments.yaml',
        target=expanduser('{}/.juju/environments.yaml'.format(HOME)),
        perms=0644,
        context={
        }
    )
    chownr('{}/.juju'.format(HOME), USER, USER)


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


def export_environment(path, name):
    environment = {}
    environment['environment'] = return_environment(name)
    with open(path, 'w+') as o_file:
        o_file.write(yaml.dump(environment,
                               default_flow_style=False))


def return_environment(name):
    env_conf = {'environment-name':name}
    with open('{}/.juju/environments.yaml'.format(HOME), 'r') as e_file:
        e_content = yaml.load(e_file)
    env_conf['environment-config'] = b64encode(
        yaml.dump(
            e_content['environments'][name],
            default_flow_style=False
        )
    )
    with open('{}/.juju/environments/{}.jenv'.format(HOME, name),
              'r') as e_file:
        e_content = e_file.read()
    env_conf['environment-jenv'] = b64encode(e_content)
    with open('{}/.juju/ssh/juju_id_rsa'.format(HOME), 'r') as e_file:
        e_content = e_file.read()
    env_conf['environment-pubkey'] = b64encode(e_content)
    with open('{}/.juju/ssh/juju_id_rsa.pub'.format(HOME), 'r') as e_file:
        e_content = e_file.read()
    env_conf['environment-privkey'] = b64encode(e_content)
    return env_conf


def import_environment(env_conf):
    name = env_conf['environment-name']
    conf = yaml.load(b64decode(env_conf['environment-config']))
    jenv = b64decode(env_conf['environment-jenv'])
    pubkey = b64decode(env_conf['environment-pubkey'])
    privkey = b64decode(env_conf['environment-privkey'])
    with open('{}/.juju/environments.yaml'.format(HOME), 'r') as e_file:
        e_content = yaml.load(e_file)
    with open('{}/.juju/environments.yaml'.format(HOME), 'w+') as e_file:
        e_content['environments'][name] = conf
        e_file.write(yaml.dump(e_content, default_flow_style=False))
    with open('{}/.juju/environments/{}.jenv'.format(HOME, name),
              'w+') as e_file:
        e_file.write(jenv)
    with open('{}/.juju/ssh/juju_id_rsa'.format(HOME), 'w+') as e_file:
        e_file.write(pubkey)
    with open('{}/.juju/ssh/juju_id_rsa.pub'.format(HOME), 'w+') as e_file:
        e_file.write(privkey)
    switch_env(name)


def switch_env(name):
    """switch to environment with given name"""
    try:
        check_output(['su',
                      '-l', USER,
                      '-c', 'juju switch {}'.format(name)], stderr=STDOUT)
    except CalledProcessError as ex:
        print ex.output
        raise
