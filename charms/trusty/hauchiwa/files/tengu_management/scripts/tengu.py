#!/usr/bin/python
# pylint: disable=C0111,c0321,c0301,c0325
#
""" deploys a tengu env """
import os
from os.path import expanduser, realpath
import shutil
import subprocess
import urllib
import tarfile
import sys
import base64
import pprint
from time import sleep
# import json
# import datetime
# from datetime import tzinfo, timedelta, datetime

# non-default pip dependencies
import click
#from dateutil.parser import parse
import yaml

# Own modules
from output import okblue, fail, okwhite
from config import Config, script_dir, tengu_dir
from jujuhelpers import JujuEnvironment
import jfed_provider


global_conf = Config("", realpath(script_dir() + "/../etc/global-conf.yaml")) # pylint: disable=c0103
DEFAULT_ENV_CONF = realpath(script_dir() + "/../templates/env-conf.yaml.template")
ENV_CONF_NAME = "env-conf.yaml"
PPRINTER = pprint.PrettyPrinter()
PROVIDER = jfed_provider.JfedProvider(global_conf)


def init_environment_config(env_name):
    """ Inits environment config.
        Does not override environment config if it exists """
    config = Config(DEFAULT_ENV_CONF, env_conf_path(env_name))
    config['env-name'] = env_name
    config.save()
    return config


def wait_for_init(env_conf):
    """Waits until VW prepare script has happened"""
    bootstrap_host = env_conf['juju-env-conf']['bootstrap-host']
    bootstrap_user = env_conf['juju-env-conf']['bootstrap-user']
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
                '{}@{}'.format(bootstrap_user, bootstrap_host),
                '[[ -f /var/log/tengu-init-done ]] && echo "1"'
            ])
        except subprocess.CalledProcessError:
            pass
        if output and output.rstrip() == '1':
            break
        sleep(5)
    sys.stdout.write('\n')


def create_juju(env_conf, provider_env):
    if JujuEnvironment.env_exists(env_conf['env-name']):
        fail("Juju environment already exists. Remove it first with 'tengu destroy {}'".format(env_conf['env-name']))
    try:
        machines = provider_env.machines
    except Exception as ex: # pylint: disable=W0703
        fail("Could not get machines from manifest", ex)
    # Create Juju environment
    env_conf['juju-env-conf']['bootstrap-host'] = machines.pop(0)
    env_conf.save()
    wait_for_init(env_conf)
    return JujuEnvironment.create(
        env_conf['env-name'],
        env_conf['juju-env-conf']['bootstrap-host'],
        env_conf['juju-env-conf'],
        machines
    )


def lock_environment(env_name, lock_status):
    env_conf = init_environment_config(env_name)
    env_conf['locked'] = lock_status
    env_conf.save()
    if lock_status:
        action = 'locked'
    else:
        action = 'unlocked'
    print "Tengu {} is {}".format(env_name, action)
#    from crontab import CronTab
#    tab = CronTab()
#    cron = tab.new(command='/foo/bar')
#    cron.every_reboot()
#    tab.write()


def env_conf_path(name):
    """ Returns path of environment config of environment with given name"""
    return tengu_dir() + "/" + name +"/"+ ENV_CONF_NAME


def destroy_juju_environment(name):
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
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
def c_add_machines(name):
    """Add machines of jfed experiment to Juju environment
    NAME: name of Tengu """
    env_conf = init_environment_config(name)
    env = PROVIDER.get(env_conf)
    machines = env.machines
    machines.pop(0)
    jujuenv = JujuEnvironment(name)
    jujuenv.add_machines(machines)

@click.command(
    name='export',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
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
    '--create-machines/--no-create-machines',
    default=True,
    help='skip creation of provider environment')
# @click.option(
#     '--clean/--no-clean',
#     default=False,
#     help='destroys juju environment before creating Tengu')
@click.argument('name')
def c_create(bundle, name, create_machines):
    """Create a Tengu with given name. Skips slice creation if it already exists.
    NAME: name of Tengu """
#    if clean:
#        destroy_juju_environment(name)
    env_conf = init_environment_config(name)
    with open(bundle, 'r') as bundle_file:
        bundledict = yaml.load(bundle_file)
    if create_machines:
        provider_env = PROVIDER.create_from_bundle(env_conf, bundledict)
    else:
        provider_env = PROVIDER.get(env_conf)
    juju_env = create_juju(env_conf, provider_env)
    juju_env.deploy_bundle(bundle)


@click.command(
    name='deploy',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '--bundle',
    type=click.Path(exists=True, readable=True),
    default='/opt/tengu/templates/bundle.yaml',
    help='path to bundle that contains machines to create and services to deploy')
@click.argument('name')
def c_deploy(bundle, name):
    """Create a Tengu with given name. Skips slice creation if it already exists.
    NAME: name of Tengu """
    juju_env = JujuEnvironment(name)
    juju_env.deploy_bundle(bundle)


@click.command(
    name='destroy',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
def c_destroy(name):
    """Destroys Tengu with given name
    NAME: name of Tengu """
    if click.confirm('Warning! This will destroy both the Juju environment and the jFed experiment of the Tengu with name {}. Are you sure you want to continue?'.format(name)):
        destroy_juju_environment(name)
        env_conf = init_environment_config(name)
        env = PROVIDER.get(env_conf)
        env.destroy()

@click.command(
    name='lock',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
def c_lock(name):
    """Lock destructive actions for given Tengu
    NAME: name of Tengu """
    lock_environment(name, True)

@click.command(
    name='unlock',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
def c_unlock(name):
    """Lock destructive actions for given Tengu
    NAME: name of Tengu """
    lock_environment(name, False)

@click.command(
    name='renew',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
@click.argument('hours', type=int, default=800)
def c_renew(name, hours):
    """ Set expiration date of Tengu to now + given hours
    NAME: name of Tengu
    HOURS: requested expiration hours"""
    okwhite('renewing slice {} for {} hours'.format(name, hours))
    env_conf = init_environment_config(name)
    env = PROVIDER.get(env_conf)
    env.renew(hours)



@click.command(
    name='status',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
def c_status(name):
    """Show status of Tengu with given name
    NAME: name of Tengu """
    env_conf = init_environment_config(name)
    env = PROVIDER.get(env_conf)
    responsedict = env.status
    if responsedict['short_status'] == 'READY':
        statusdict = responsedict['json_output']
        try:
            okblue("status of jfed slice is {}".format(statusdict['AMs'].values()[0]['amGlobalSliverStatus']))
            okblue("earliest expiration date of sliver is {}".format(statusdict['earliestSliverExpireDate']))
        except (yaml.parser.ParserError, ValueError, KeyError) as exc:
            print("could not parse status from ouptut. statusdict: ")
            PPRINTER.pprint(statusdict)
            raise exc
    else:
        okwhite("status of jfed slice is {}. responsedict: ".format(responsedict['short_status']))
        PPRINTER.pprint(responsedict)
    if JujuEnvironment.env_exists(name):
        okblue('Juju environment exists')
    else:
        okwhite("Juju environment doesn't exist")

@click.command(
    name='export',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-n', '--name',
    default=JujuEnvironment.current_env(),
    help='Name of Tengu. Defaults to name of current Juju environment.')
@click.argument(
    'path',
    type=click.Path(writable=True))
def c_export(name, path):
    """Export Tengu with given NAME"""
    jujuenv = JujuEnvironment(name)
    config = jujuenv.return_environment()
    files = {
        "tengu-env-conf" : env_conf_path(name),
    }
    env_conf = init_environment_config(name)
    env = PROVIDER.get(env_conf)
    files.update(env.files)
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
    """Import Tengu from config file"""
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
    }
    env_conf = init_environment_config(name)
    env = PROVIDER.get(env_conf)
    files.update(env.files)
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
    PPRINTER.pprint(PROVIDER.userinfo)

@click.command(
    name='downloadbigfiles',
    context_settings=CONTEXT_SETTINGS)
def c_downloadbigfiles():
    """ Download bigfiles in $JUJU_REPOSITORY """
    downloadbigfiles(os.environ['JUJU_REPOSITORY'])

# @click.command(
#     name='c_renew_if_closer_than'
# )
# @click.option(
#     '-n', '--name',
#     default=JujuEnvironment.current_env(),
#     help='Name of Tengu. Defaults to name of current Juju environment.')
# @click.argument(
#     'mindays',
#     type=int,
#     default=7)
# def c_renew_if_closer_than(name, mindays):
#     #TODO: clean this up once we switch to python 3
#     # http://stackoverflow.com/a/25662061/1588555
#     ZERO = timedelta(0)#pylint: disable=c0103
#     class UTC(tzinfo):
#         def utcoffset(self, dt):#pylint: disable=w0613
#             return ZERO
#         def tzname(self, dt):#pylint: disable=w0613
#             return "UTC"
#         def dst(self, dt):#pylint: disable=w0613
#             return ZERO
#     utc = UTC()
#
#     jfed = init_jfed(name, global_conf)
#     status = jfed.get_full_status()
#     if status.lstrip().rstrip() != 'DOES_NOT_EXIST':
#         try:
#             statusdict = json.loads(status)
#             earliestexpdate = parse(statusdict['earliestSliverExpireDate'])
#             now = datetime.now(utc)
#             difference = earliestexpdate - now
#             status_message = "sliver expires {}\ntoday is {}\ndifference is {}\nmindays is {}".format(earliestexpdate, now, difference, mindays)
#             print(status_message)
#             if difference.days < mindays:
#                 hourstorenew = 800
#                 print('renewing slice for {} hours'.format(hourstorenew))
#                 jfed = init_jfed(name, global_conf)
#                 try:
#                     jfed.renew(hourstorenew)
#                 except Exception as ex: #pylint:disable=W0703
#                     mail('renewing slice for {} hours failed. Status: {}'.format(hourstorenew, status_message))
#                     fail('renewing slice failed', ex)
#                 print('renewed slice succesfully')
#             else:
#                 print('not renewing slice')
#         except (yaml.parser.ParserError, ValueError, KeyError) as exc:
#             print("could not parse status from ouptut. output: " + status)
#             raise exc
#     else:
#         fail("experiment {} doesn't exist".format(name))



g_cli.add_command(c_create)
g_cli.add_command(c_deploy)
g_cli.add_command(c_destroy)
g_cli.add_command(c_lock)
g_cli.add_command(c_unlock)
g_cli.add_command(c_renew)
g_cli.add_command(c_status)
g_cli.add_command(c_userinfo)
g_cli.add_command(c_export)
g_cli.add_command(c_import)
g_cli.add_command(c_downloadbigfiles)
#g_cli.add_command(c_renew_if_closer_than)
g_cli.add_command(g_juju)
if __name__ == '__main__':
    g_cli()
