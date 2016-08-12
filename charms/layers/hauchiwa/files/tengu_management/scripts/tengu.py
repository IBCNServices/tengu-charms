#!/usr/bin/python
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
# pylint: disable=C0111,c0321,c0301,c0325
#
import os
from os.path import expanduser, realpath
import shutil
import subprocess
import urllib
import tarfile
import base64
import pprint
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
from jujuhelpers import JujuEnvironment, Service
import jfed_provider
import ssh_provider
import juju_powered_provider


GLOBAL_CONF = Config(realpath(script_dir() + "/../etc/global-conf.yaml")) # pylint: disable=c0103
DEFAULT_ENV_CONF = realpath(script_dir() + "/../templates/env-conf.yaml.template")
ENV_CONF_NAME = "env-conf.yaml"
PPRINTER = pprint.PrettyPrinter()
DEFAULT_ENV = JujuEnvironment.current_env()


def get_provider(config=GLOBAL_CONF):
    provider = config.get('provider', 'rest2jfed')
    if provider == "ssh":
        return ssh_provider.SSHProvider(GLOBAL_CONF)
    elif provider == "rest2jfed":
        return jfed_provider.JfedProvider(GLOBAL_CONF)
    elif provider == "juju-powered":
        return juju_powered_provider.JujuPoweredProvider(GLOBAL_CONF)
    else:
        fail("No provider of type {} found".format(provider))


def env_conf_path(name):
    """ Returns path of environment config of environment with given name"""
    return tengu_dir() + "/" + name +"/"+ ENV_CONF_NAME

def init_environment_config(env_name):
    """ Returns environment config. Creates config if it doesn't exist yet."""
    config = Config(env_conf_path(env_name), default_path=DEFAULT_ENV_CONF)
    config['env-name'] = env_name
    config.save()
    return config


def lock_environment(env_name, lock_status):
    env_conf = init_environment_config(env_name)
    env_conf['locked'] = lock_status
    env_conf.save()
    if lock_status:
        action = 'locked'
    else:
        action = 'unlocked'
    print "Model {} is {}".format(env_name, action)
#    from crontab import CronTab
#    tab = CronTab()
#    cron = tab.new(command='/foo/bar')
#    cron.every_reboot()
#    tab.write()


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
    if path == "":
        okwhite("No repository specified, will not download bigfiles")
        return
    # The top argument for walk
    topdir = os.path.realpath(path)
    okwhite("downloading bigfiles in %s " % topdir)
    # The extension to search for
    exten = '.source'
    # Walk through the directories
    for dirpath, dirnames, files in os.walk(topdir): #pylint:disable=w0612
        # for all files in current directory
        for name in files:
            # If file is source file
            if name.lower().endswith(exten):
                source_path = os.path.join(dirpath, name)
                dest_path = source_path[:-len(exten)]
                # If file to download doesn't exist
                if not os.path.isfile(dest_path):
                    okwhite('{}'.format(dest_path))
                    with open(source_path, "r") as source_file:
                        first_line = source_file.readline().rstrip()
                        action = source_file.readline().rstrip()
                    # If source file contains download command
                    if first_line.startswith('command: '):
                        command = first_line.lstrip('command: ')
                        subprocess.check_output(
                            [command], shell=True, cwd=dirpath
                        )
                    # if source file contains url
                    else:
                        url = first_line
                        okwhite('\t DOWNLOADING FROM: %s' % url)
                        urlopener = urllib.URLopener()
                        urlopener.retrieve(url, dest_path)
                    # if source file contains extract action
                    if action == "extract":
                        okwhite('\t EXTRACTING: %s' % dest_path)
                        tfile = tarfile.open(dest_path, 'r')
                        # Important to note that the following extraction is
                        # UNSAFE since .tar.gz archive could contain
                        # relative path like ../../ and overwrite other dirs
                        tfile.extractall(os.path.dirname(dest_path))
    okwhite("downloading bigfiles complete")


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(name='juju', context_settings=CONTEXT_SETTINGS)
def g_juju():
    """ Juju related commands """
    pass

@click.command(
    name='add-machines',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
def c_add_machines(model):
    """Add machines of jfed experiment to Juju environment
    NAME: name of model """
    env_conf = init_environment_config(model)
    env = get_provider(env_conf).get(env_conf)
    machines = env.machines
    machines.pop(0)
    jujuenv = JujuEnvironment(model)
    jujuenv.add_machines(machines)

@click.command(
    name='export',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
@click.argument('filename')
def c_export_juju_env(model, filename):
    """export juju environment to given yaml file """
    jujuenv = JujuEnvironment(model)
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
    name='create-model',
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
@click.argument('name')
def c_create_model(bundle, name, create_machines):
    """Create a model with given name. Skips slice creation if it already exists.
    NAME: name of model """
    env_conf = init_environment_config(name)
    try:
        with open(bundle, 'r') as bundle_file:
            bundledict = yaml.load(bundle_file)
    except yaml.YAMLError as yamlerror:
        raise click.ClickException('Parsing bundle \033[91mfailed\033[0m: {}'.format(str(yamlerror)))
    downloadbigfiles(os.environ.get('JUJU_REPOSITORY', ''))
    if create_machines:
        provider_env = get_provider(env_conf).create_from_bundle(env_conf, bundledict)
    else:
        provider_env = get_provider(env_conf).get(env_conf)
    juju_env = JujuEnvironment.create(
        env_conf['env-name'],
        env_conf['juju-env-conf'],
        provider_env.machines,
        env_conf['init-bundle'],
    )
    juju_env.deploy_bundle(bundle)


@click.command(
    name='lock-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name', type=str)
def c_lock_model(name):
    """Lock destructive actions (such as destroy and reload) for given model.
    NAME: name of model """
    lock_environment(name, True)


@click.command(
    name='unlock-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name', type=str)
def c_unlock_model(name):
    """Unlock destructive actions (such as destroy, reload) for given model.
    NAME: name of model """
    lock_environment(name, False)


@click.command(
    name='reload-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name', type=str)
def c_reload_model(name):
    """ Reload the model's machines. This will completely wipe the disk of the machines and put a new OS on them.
    NAME: name of model
    """
    if click.confirm('Warning! This will wipe the disk of all the machines of the model "{}". Are you sure you want to continue?'.format(name)):
        okwhite('reloading all slivers in slice {}'.format(name))
        env_conf = init_environment_config(name)
        env = get_provider(env_conf).get(env_conf)
        env.reload()


@click.command(
    name='reset-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument('modelname', type=str)
def c_reset_model(modelname):
    """ Destroys the model's services and containers except for lxc-networking, dhcp-server and openvpn.
    if whitelist is provided, only services in whitelist will be destroyed.
    NAME: name of model
    WHITELIST: names of charms to destroy
    """
    if click.confirm('Warning! This will remove all services and containers of the model "{}". Are you sure you want to continue?'.format(modelname)):
        env_conf = init_environment_config(modelname)
        if env_conf['locked']:
            fail('Cannot reset locked environment')
        else:
            jujuenv = JujuEnvironment(modelname)
            for servicename in jujuenv.status['services'].keys():
                if servicename not in ['lxc-networking', 'dhcp-server', 'openvpn']: # We should get these services from the init bundle...
                    Service(servicename, jujuenv).destroy(force=True)


@click.command(
    name='destroy-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument('name', type=str)
def c_destroy_model(name):
    """Destroys model with given name
    NAME: name of model """
    if click.confirm('Warning! This will destroy both the Juju environment and the jFed experiment of the model "{}". Are you sure you want to continue?'.format(name)):
        destroy_juju_environment(name)
        env_conf = init_environment_config(name)
        env = get_provider(env_conf).get(env_conf)
        env.destroy()


@click.command(
    name='destroy-service',
    context_settings=CONTEXT_SETTINGS)
@click.argument('modelname', type=str)
@click.argument('services', nargs=-1)
def c_destroy_service(modelname, services):
    """Destroys given services
    MODELNAME: name of the model
    SERVICES: services to destroy"""
    jujuenv = JujuEnvironment(modelname)
    for servicename in jujuenv.status['services'].keys():
        if servicename in services:
            Service(servicename, jujuenv).destroy(force=True)


@click.command(
    name='renew-model',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
@click.argument('hours', type=int, default=800)
def c_renew_model(model, hours):
    """ Set expiration date of the model's underlying jFed experiment to now + given hours
    NAME: name of model
    HOURS: requested expiration hours"""
    okwhite('renewing slice {} for {} hours'.format(model, hours))
    env_conf = init_environment_config(model)
    env = get_provider(env_conf).get(env_conf)
    env.renew(hours)


@click.command(
    name='expose-service',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
@click.argument('servicename')
def c_expose_service(model, servicename):
    """ Expose the service so it is publicly available from the internet.
    NAME: name of model
    SERVICENAME: name of the service to expose"""
    env_conf = init_environment_config(model)
    provider_env = get_provider(env_conf).get(env_conf)
    env_conf = init_environment_config(model)
    env = JujuEnvironment(model)
    service = Service(servicename, env)
    provider_env.expose(service)


@click.command(
    name='show-config',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Get the config of a service in a format that can be used to set the config of a service.')
@click.argument('servicename')
def c_show_config(model, servicename):
    """Get the config of a service in a format that can be used to set the config of a service.
    NAME: name of model
    SERVICENAME: name of the service"""
    env = JujuEnvironment(model)
    service = Service(servicename, env)
    print(yaml.dump({str(servicename): service.get_config()}, default_flow_style=False))


@click.command(
    name='show-status',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
def c_show_status(model):
    """Show status of model with given name
    NAME: name of model """
    env_conf = init_environment_config(model)
    env = get_provider(env_conf).get(env_conf)
    responsedict = env.status
    if responsedict['short_status'] == 'READY':
        statusdict = responsedict['json_output']
        try:
            okblue("Status of experiment is {}".format(statusdict['AMs'].values()[0]['amGlobalSliverStatus']))
            okblue("Experiment will expire at {}".format(statusdict['earliestSliverExpireDate']))
        except (yaml.parser.ParserError, ValueError, KeyError) as exc:
            print("could not parse status from ouptut. statusdict: ")
            PPRINTER.pprint(statusdict)
            raise exc
    else:
        okwhite("Status of jfed slice is {}. responsedict: ".format(responsedict['short_status']))
        PPRINTER.pprint(responsedict)
    if JujuEnvironment.env_exists(model):
        okblue('Juju environment exists')
    else:
        okwhite("Juju environment doesn't exist")


@click.command(
    name='export-model',
    context_settings=CONTEXT_SETTINGS)
@click.option(
    '-m', '--model',
    default=DEFAULT_ENV,
    help='Name of model. Defaults to the active model.')
@click.argument(
    'path',
    type=click.Path(writable=True))
def c_export_model(model, path):
    """Export the config of the model with given NAME"""
    jujuenv = JujuEnvironment(model)
    config = jujuenv.return_environment()
    files = {
        "tengu-env-conf" : env_conf_path(model),
    }
    env_conf = init_environment_config(model)
    env = get_provider(env_conf).get(env_conf)
    files.update(env.files)
    for f_name, f_path in files.iteritems():
        with open(f_path, 'r') as f_file:
            config[f_name] = base64.b64encode(f_file.read())
    config['emulab-project-name'] = GLOBAL_CONF['project-name']
    export = {
        str(model) : config
    }
    with open(path, 'w+') as outfile:
        outfile.write(yaml.dump(export))


@click.command(
    name='import-model',
    context_settings=CONTEXT_SETTINGS)
@click.argument(
    'path',
    type=click.Path(exists=True, readable=True))
def c_import_model(path):
    """Import model config from config file"""
    with open(path, 'r') as stream:
        export = yaml.load(stream)
    name = export.keys()[0]
    config = export.values()[0]
    if not os.path.isdir(os.path.dirname(env_conf_path(name))):
        os.makedirs(os.path.dirname(env_conf_path(name)))
    elif not click.confirm('Warning! Model "{}" already configured, are you sure you want to overwrite the config files?'.format(name)):
        exit()
    files = {
        "tengu-env-conf" : env_conf_path(name),
    }
    env_conf = init_environment_config(name)
    env = get_provider(env_conf).get(env_conf)
    files.update(env.files)
    for f_key, f_path in files.iteritems():
        with open(f_path, 'w+') as f_file:
            f_file.write(base64.b64decode(config[f_key]))
    GLOBAL_CONF['project_name'] = config['emulab-project-name']
    GLOBAL_CONF.save()
    JujuEnvironment.import_environment(config)


@click.command(
    name='show-userinfo',
    context_settings=CONTEXT_SETTINGS)
def c_show_userinfo():
    """ Print info of configured jfed user """
    PPRINTER.pprint(get_provider().userinfo)


@click.command(
    name='downloadbigfiles',
    context_settings=CONTEXT_SETTINGS)
def c_downloadbigfiles():
    """ Download bigfiles in $JUJU_REPOSITORY """
    downloadbigfiles(os.environ.get('JUJU_REPOSITORY', ''))

# @click.command(
#     name='c_renew_if_closer_than'
# )
# @click.option(
#     '-m', '--model',
#     default=DEFAULT_ENV,
#     help='Name of model. Defaults to the active model.')
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
#     jfed = init_jfed(name, GLOBAL_CONF)
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
#                 jfed = init_jfed(name, GLOBAL_CONF)
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



g_cli.add_command(c_create_model)
g_cli.add_command(c_destroy_model)
g_cli.add_command(c_destroy_service)
g_cli.add_command(c_reload_model)
g_cli.add_command(c_reset_model)
g_cli.add_command(c_lock_model)
g_cli.add_command(c_unlock_model)
g_cli.add_command(c_renew_model)
g_cli.add_command(c_show_status)
g_cli.add_command(c_show_userinfo)
g_cli.add_command(c_show_config)
g_cli.add_command(c_expose_service)
g_cli.add_command(c_export_model)
g_cli.add_command(c_import_model)
g_cli.add_command(c_downloadbigfiles)
#g_cli.add_command(c_renew_if_closer_than)
g_cli.add_command(g_juju)
if __name__ == '__main__':
    g_cli()
