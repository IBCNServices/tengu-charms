#!/usr/bin/python
# pylint: disable=C0111,c0321,c0301,c0325
#
""" deploys a tengu env """
import os
from os.path import expanduser, realpath
import shutil
from Crypto.PublicKey import RSA
import subprocess
import urllib
import tarfile
from time import sleep
import sys
import json
import base64

# non-default pip dependencies
import yaml
import click


# Own modules
from rest2jfed_connector import Rest2jfedConnector # pylint: disable=F0401
import rspec_utils                                 # pylint: disable=F0401
from output import okblue, fail, okwhite           # pylint: disable=F0401
from config import Config, script_dir, tengu_dir   # pylint: disable=F0401
from jujuhelpers import JujuEnvironment            # pylint: disable=F0401

global_conf = Config("", realpath(script_dir() + "/../etc/global-conf.yaml")) # pylint: disable=c0103
DEFAULT_ENV_CONF = realpath(script_dir() + "/../templates/env-conf.yaml.template")
ENV_CONF_NAME = "env-conf.yaml"


def init_environment_config(env_name, rspec=None):
    """ Inits environment config.
        Does not override environment config if it exists """
    config = Config(DEFAULT_ENV_CONF, env_conf_path(env_name))
    if os.path.isfile(rspec_path(env_name)):
        okwhite("rspec already present, not overwriting")
    elif rspec:
        okwhite('new rspec, writing to {}'.format(rspec_path(env_name)))
        with open(rspec_path(env_name), 'w+') as rspec_file:
            rspec_file.write(rspec)
    else:
        fail('rspec not found and no rspec given')
    config['rspec_path'] = rspec_path(env_name)
    config['manifest_path'] = manifest_path(env_name)
    config['env_name'] = env_name
    config.save()
    return config


def init_jfed(env_name, locked=True):
    return Rest2jfedConnector(global_conf['rest2jfed_hostname'],
                              global_conf['rest2jfed_port'],
                              global_conf['s4_cert_path'],
                              global_conf['project_name'],
                              env_name,
                              locked=locked)


def init_bare_jfed():
    return init_jfed(None, locked=True)


def create_from_bundle(env_name, bundle_path):
    if not os.path.isfile(bundle_path):
        fail("cannot find bundle at {}".format(bundle_path))
    with open(bundle_path, 'r') as bundle_file:
        bundle = yaml.load(bundle_file)
    data = get_data_from_bundle(bundle)
    create_env(env_name, data['nrnodes'], data['pub_ipv4'], data['testbed'])
    deploy_bundle(bundle_path)


def count_machines(bundle_path):
    with open(bundle_path, 'r') as bundle_file:
        bundle = yaml.load(bundle_file)
    return len(bundle['machines'])


def deploy_bundle(bundle_path):
    command = ['juju', 'deployer', '-c', bundle_path]
    subprocess.check_output(command)

def get_data_from_bundle(bundle):
    machines = bundle.get('machines')
    if not machines: fail('Could not find machines item in bundle.')
    if not len(machines) > 0: fail('There has to be at least 1 machine specified')
    testbed = None
    pub_ipv4 = False
    for m_id in range(len(machines)):
        if not machines.get(str(m_id)): fail('machine {} not found while number of machines is {}.'.format(m_id, len(machines)))
        if m_id == 0:
            constraints = machines[str(m_id)].get('constraints').split()
            for constraint in constraints:
                if constraint.startswith('testbed='):
                    testbed = constraint.split('=')[1]
                elif constraint.startswith('pubipv4=') and constraint.split('=')[1].lower() == 'true':
                    pub_ipv4 = True
            if not testbed: fail("machine {} doesn't specify testbed.".format(m_id))
    return {
        'nrnodes' : len(machines),
        'testbed' : testbed,
        'pub_ipv4' : pub_ipv4,
    }


def create_virtualwall(env_conf, jfed):
    """Deploys a tengu env"""
    okwhite('checking if jfed exp exists..')
    if jfed.exp_exists():
        okwhite("jfed exp exists")
        if os.path.isfile(env_conf['manifest_path']):
            okwhite("jFed experiment exists, downloading manifest")
            jfed.get_manifest(env_conf['manifest_path'])
    else:
        okwhite("jFed experiment doesn't exist, creating one now.")
        try:
            jfed.create(env_conf['rspec_path'], env_conf['manifest_path'])
        except Exception as ex: # pylint: disable=W0703
            fail('Creation of JFed experiment failed', ex)


def wait_for_init(env_conf):
    """Waits until VW prepare script has happened"""
    bootstrap_host = env_conf['bootstrap_host']
    okwhite('Waiting for {} to finish partition resize'.format(bootstrap_host))
    output = None
    while True:
        sys.stdout.write('.')
        sys.stdout.flush()
        try:
            output = subprocess.check_output([
                'ssh',
                '-o',
                'StrictHostKeyChecking=no',
                'jujuuser@{}'.format(bootstrap_host),
                '[[ -f /var/log/tengu-init-done ]] && echo "1"'
            ])
        except subprocess.CalledProcessError:
            pass
        if output and output.rstrip() == '1':
            break
        sleep(5)
    sys.stdout.write('\n')


def create_juju(env_conf):
    if JujuEnvironment.env_exists(env_conf['env_name']):
        fail("Juju environment already exists. Remove it first with 'tengu destroy {}'".format(env_conf['env_name']))
    try:
        machines = rspec_utils.get_machines(env_conf['manifest_path'])
    except Exception as ex: # pylint: disable=W0703
        fail("Could not get machines from manifest", ex)
    # Create Juju environment
    env_conf['bootstrap_host'] = machines.pop(0)
    env_conf.save()
    wait_for_init(env_conf)
    JujuEnvironment.create(env_conf['env_name'],
                           env_conf['bootstrap_host'],
                           env_conf['juju_env_conf'],
                           machines)


def create_env(env_name, nodes=5, pub_ipv4=0, testbed='wall1'):
    jfed = init_jfed(env_name, global_conf)
    userkeys = [{
        'user' : 'jujuuser',
        'pubkey' : get_or_create_ssh_key()
    }]
    rspec = rspec_utils.create_rspec(nodes, userkeys, pub_ipv4, testbed)
    env_conf = init_environment_config(env_name, rspec=rspec)
    create_virtualwall(env_conf, jfed)
    env_conf['locked'] = 'False'
    env_conf['juju_env_conf']['bootstrap-user'] = 'jujuuser'
    env_conf.save()
    create_juju(env_conf)


def lock_environment(env_name, lock_status):
    env_conf = init_environment_config(env_name)
    env_conf['locked'] = lock_status
    env_conf.save()


def env_conf_path(name):
    """ Returns path of environment config of environment with given name"""
    return tengu_dir() + "/" + name +"/"+ ENV_CONF_NAME

def rspec_path(name):
    """ Returns path of rspec of environment with given name"""
    return tengu_dir() + "/" + name +"/"+ "juju-tengu.rspec"

def manifest_path(name):
    """ Returns path of manifest of environment with given name"""
    return tengu_dir() +"/"+ name +"/"+ "manifest.mrspec"

def destroy_environment(name):
    """ Destroy Juju environment and destroy Juju environment config files """
    env_conf = init_environment_config(name)
    if env_conf['locked']:
        fail('Cannot destroy locked environment')
    else:
        okwhite("removing juju environment from juju config files")
        with open(expanduser("~/.juju/environments.yaml"), 'r') as config_file:
            config = yaml.load(config_file)
        if config['environments'] is not None:
            config['environments'].pop(name, None)
        with open(expanduser("~/.juju/environments.yaml"), 'w') as config_file:
            config_file.write(yaml.dump(config, default_flow_style=False))
        okwhite("removing juju environment from juju environment folder")
        if os.path.isfile(expanduser("~/.juju/environments/%s.jenv" % name)):
            os.remove(expanduser("~/.juju/environments/%s.jenv" % name))


def ensure_exists(default, dest):
    """ If dest doesn't exist, copy it from default """
    if not os.path.isfile(dest):
        shutil.copyfile(default, dest)


def get_or_create_ssh_key():
    """ Gets ssh key. Creates one if it doesn't exist yet. """
    ssh_pub_keypath = expanduser("~/.ssh/id_rsa.pub")
    ssh_priv_keypath = expanduser("~/.ssh/id_rsa")
    if os.path.isfile(ssh_pub_keypath):
        with open(ssh_pub_keypath, 'r') as pubkeyfile:
            return pubkeyfile.read().rstrip()
    else:
        key = RSA.generate(2048)
        with open(ssh_priv_keypath, 'w+') as privkeyfile:
            privkeyfile.write(key.exportKey())
        os.chmod(ssh_priv_keypath, 0o600)
        with open(ssh_pub_keypath, 'w+') as pubkeyfile:
            pubkey = key.publickey().exportKey('OpenSSH')
            pubkeyfile.write(pubkey + "\n")
        return pubkey


def get_bootstrap_user(env_conf):
    """ Gets bootstrap-user if it exists. Set jujuuser as bootstrap-user
        if it doesn't exist. For this to work, this user and its pubkey should
        be added to the rspec """
    username = env_conf['juju_env_conf'].get('bootstrap-user')
    if username:
        return username
    else:
        # username must not be longer than 8 chars! Emulab requirement!
        env_conf['juju_env_conf']['bootstrap-user'] = 'jujuuser'
        env_conf.save()
        return 'jujuuser'


def add_pubkey_to_rspec(env_name, env_conf):
    """ adds """
    pubkey = get_or_create_ssh_key()
    rspec_utils.add_pubkey_to_rspec(\
        rspec_path(env_name),
        get_bootstrap_user(env_conf),
        pubkey)


def destroy_jfed_exp(_env_name):
    env_conf = init_environment_config(_env_name)
    jfed = init_jfed(_env_name, locked=env_conf['locked'])
    jfed.delete()
    okwhite("Slice deleted")


def downloadbigfiles(path):
    """Downloads url from .source files it finds in path"""
    # The top argument for walk
    topdir = os.path.realpath(path)
    okwhite("downloading sources in %s " % topdir)
    # The extension to search for
    exten = '.source'
    for dirpath, dirnames, files in os.walk(topdir): #pylint:disable=w0612
        for name in files:
            if name.lower().endswith(exten):
                source = os.path.join(dirpath, name)
                file_to_download = source[:-len(exten)]
                okwhite('%s' % file_to_download)

                if not os.path.isfile(file_to_download):
                    with open(source, "r") as myfile:
                        url = myfile.readline().rstrip()
                        command = myfile.readline().rstrip()
                    if url.startswith('command: '):
                        command = url.lstrip('command: ')
                        subprocess.check_output(
                            [command], shell=True, cwd=dirpath
                        )
                    else:
                        okwhite('\t DOWNLOADING FROM: %s' % url)
                        urlopener = urllib.URLopener()
                        urlopener.retrieve(url, file_to_download)
                        if command == "extract":
                            okwhite('\t EXTRACTING: %s' % file_to_download)
                            tfile = tarfile.open(file_to_download, 'r')
                            # Important to note that the following extraction is
                            # UNSAFE since .tar.gz archive could contain
                            # relative path like ../../ and overwrite other dirs
                            tfile.extractall(os.path.dirname(file_to_download))
                else:
                    okwhite('\t OK')
                okwhite('')

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(name='juju', context_settings=CONTEXT_SETTINGS)
def g_juju():
    """ Juju related commands """
    pass

@click.command(
    name='add-machines',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
def c_add_machines(name):
    """Add machines of jfed experiment to Juju environment
    NAME: name of Kotengu """
    env_conf = init_environment_config(name)
    machines = rspec_utils.get_machines(env_conf['manifest_path'])
    machines.pop(0)
    jujuenv = JujuEnvironment(name)
    jujuenv.add_machines(machines)

@click.command(
    name='export',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
@click.argument('filename')
def c_export_juju_env(name, filename):
    """export juju environment to given yaml file """
    jujuenv = JujuEnvironment(name)
    environment = {}
    environment['environment'] = jujuenv.return_environment()
    with open(filename, 'w+') as o_file:
        o_file.write(yaml.dump(environment, default_flow_style=False))



g_juju.add_command(c_add_machines)
g_juju.add_command(c_export_juju_env)


@click.group()
def g_cli():
    pass

@click.command(
    name='create',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '--bundle',
    type=click.Path(exists=True, readable=True),
    default='/opt/tengu/templates/bundle.yaml',
    help='path to bundle that contains machines to create and services to deploy')
@click.option(
    '--clean/--no-clean',
    default=False,
    help='destroys juju environment before creating Kotengu')
@click.argument('name')
def c_create(bundle, name, clean):
    """Create a Kotengu with given name. Skips slice creation if it already exists.
    NAME: name of Kotengu """
    if clean:
        destroy_environment(name)
    create_from_bundle(name, bundle)

@click.command(
    name='destroy',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
def c_destroy(name):
    """Destroys Kotengu with given name
    NAME: name of Kotengu """
    if click.confirm('Warning! This will destroy both the Juju environment and the jFed experiment. Are you sure you want to continue?'):
        destroy_environment(name)
        destroy_jfed_exp(name)

@click.command(
    name='lock',
    context_settings=CONTEXT_SETTINGS)
@click.option('--lock/--no-lock', default=False)
@click.argument('name')
def c_lock(name, lock):
    """Lock destructive actions for given Kotengu
    NAME: name of Kotengu """
    lock_environment(name, lock)

@click.command(
    name='renew',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
@click.argument('hours', type=int, default=800)
def c_renew(name, hours):
    """ Set expiration date of Kotengu to now + given hours
    NAME: name of Kotengu
    HOURS: requested expiration hours"""
    okwhite('renewing slice {} for {} hours'.format(name, hours))
    jfed = init_jfed(name, global_conf)
    try:
        #TODO: Really check if renewing slice failed.
        jfed.renew(hours)
    except Exception as ex: #pylint:disable=W0703
        fail('renewing slice failed', ex)

@click.command(
    name='status',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
def c_status(name):
    """Show status of Kotengu with given name
    NAME: name of Kotengu """
    jfed = init_jfed(name, global_conf)
    status = jfed.get_full_status()
    if status.lstrip().rstrip() != 'DOES_NOT_EXIST':
        try:
            statusdict = json.loads(status)
            okblue("status of jfed slice is {}".format(statusdict['AMs'].values()[0]['amGlobalSliverStatus']))
            okblue("earliest expiration date of sliver is {}".format(statusdict['earliestSliverExpireDate']))
        except (yaml.parser.ParserError, ValueError, KeyError) as exc:
            print("could not parse status from ouptut. output: " + status)
            raise exc
        #info = jfed.get_sliceinfo()
        #okblue("slice Expiration date: {}".format(info['sliceExpiration']))
        #okblue("slice urn date: {}".format(info['sliceUrn']))
        #okblue("user urn date: {}".format(info['userUrn']))
        #okblue("speaksfor?: {}".format(info['usedSpeaksfor']))
    else:
        okwhite("status of jfed slice is {}".format(status))
    if JujuEnvironment.env_exists(name):
        okblue('Juju environment exists')
    else:
        okwhite("Juju environment doesn't exist")

@click.command(
    name='export',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name')
@click.argument(
    'path',
    type=click.Path(writable=True))
def c_export(name, path):
    """Export Kotengu with given NAME"""
    jujuenv = JujuEnvironment(name)
    config = jujuenv.return_environment()
    files = {
        "tengu-env-conf" : env_conf_path(name),
        "rspec" : rspec_path(name),
        "manifest" : manifest_path(name),
        "emulab-s4-cert" : global_conf['s4_cert_path'],
    }
    for f_name, f_path in files.iteritems():
        with open(f_path, 'r') as f_file:
            config[f_name] = base64.b64encode(f_file.read())
    config['emulab-project-name'] = global_conf['project_name']
    export = {
        str(name) : config
    }
    with open(path, 'w+') as outfile:
        outfile.write(yaml.dump(export))

@click.command(
    name='import',
    context_settings=CONTEXT_SETTINGS)
@click.argument(
    'path',
    type=click.Path(exists=True, readable=True))
def c_import(path):
    """Import Kotengu from config file"""
    with open(path, 'r') as stream:
        export = yaml.load(stream)
    name = export.keys()[0]
    config = export.values()[0]
    if not os.path.isdir(os.path.dirname(env_conf_path(name))):
        os.makedirs(os.path.dirname(env_conf_path(name)))
    elif not click.confirm('Warning! Tengu with name {} already configured, are you sure you want to overwrite the config files?'.format(name)):
        exit()
    files = {
        "tengu-env-conf" : env_conf_path(name),
        "rspec" : rspec_path(name),
        "manifest" : manifest_path(name),
        "emulab-s4-cert" : global_conf['s4_cert_path'],
    }
    for f_key, f_path in files.iteritems():
        with open(f_path, 'w+') as f_file:
            f_file.write(base64.b64decode(config[f_key]))
    global_conf['project_name'] = config['emulab-project-name']
    global_conf.save()
    JujuEnvironment.import_environment(config)


@click.command(
    name='userinfo',
    context_settings=CONTEXT_SETTINGS)
def c_userinfo():
    """ Print info of configured jfed user """
    jfed = init_bare_jfed()
    okwhite(jfed.get_userinfo())

@click.command(
    name='downloadbigfiles',
    context_settings=CONTEXT_SETTINGS)
def c_downloadbigfiles():
    """ Download bigfiles in /opt/tengu-charms repository """
    downloadbigfiles('/opt/tengu-charms')



g_cli.add_command(c_create)
g_cli.add_command(c_destroy)
g_cli.add_command(c_lock)
g_cli.add_command(c_renew)
g_cli.add_command(c_status)
g_cli.add_command(c_userinfo)
g_cli.add_command(c_export)
g_cli.add_command(c_import)
g_cli.add_command(c_downloadbigfiles)
g_cli.add_command(g_juju)

if __name__ == '__main__':
    g_cli()
