#!/usr/bin/python
# pylint: disable=C0111
#
""" deploys a tengu env """
import os
from os.path import expanduser, realpath
import shutil
import yaml
import sys
from Crypto.PublicKey import RSA
import subprocess
import urllib
import tarfile


# Own modules
from rest2jfed_connector import Rest2jfedConnector # pylint: disable=F0401
import rspec_utils                                 # pylint: disable=F0401
from output import okblue, fail, okwhite           # pylint: disable=F0401
from config import Config, script_dir, tengu_dir   # pylint: disable=F0401
from juju_environment import JujuEnvironment       # pylint: disable=F0401

LIB_PATH = realpath(script_dir() + "/../lib")
GLOBAL_CONF = realpath(script_dir() + "/../etc/global-conf.yaml")
DEFAULT_ENV_CONF = realpath(\
                script_dir() + "/../templates/env-conf.yaml.template")
ENV_CONF_NAME = "env-conf.yaml"


def init_global_config():
    global_conf = Config("", GLOBAL_CONF)
    return  global_conf #env config must be present


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


def init_jfed(env_name, global_conf, locked=True):
    return Rest2jfedConnector(global_conf['rest2jfed_hostname'],
                              global_conf['rest2jfed_port'],
                              global_conf['s4_cert_path'],
                              global_conf['project_name'],
                              env_name,
                              locked=locked)


def init_bare_jfed(global_conf):
    return init_jfed(None, global_conf, locked=True)


def create_virtualwall(env_name, env_conf, jfed):
    """Deploys a tengu env"""
    if jfed.exp_exists() and not os.path.isfile(env_conf['manifest_path']):
        print "jFed experiment exists, downloading manifest"
        if not jfed.download_manifest(env_conf['manifest_path']):
            fail('Manifest download failed')
    else:
        print "jFed experiment doesn't exist, making one now."
        try:
            jfed.create(env_conf['rspec_path'], env_conf['manifest_path'])
        except Exception as ex: # pylint: disable=W0703
            fail('Creation of JFed experiment failed', ex)


def create_juju(env_conf):
    if JujuEnvironment.env_exists(env_conf['env_name']):
        fail("Juju environment already exists")
    try:
        machines = rspec_utils.get_machines(env_conf['manifest_path'])
    except Exception as ex: # pylint: disable=W0703
        fail("Could not get machines from manifest", ex)
    # Create Juju environment
    bootstrap_host = machines.pop(0)
    JujuEnvironment.create(env_conf['env_name'],
                           bootstrap_host,
                           env_conf['juju_env_conf'],
                           machines)


def create_env(env_name, nodes=5, public_ipv4=0):
    global_conf = init_global_config()
    jfed = init_jfed(env_name, global_conf)
    userkeys = [{
        'user' : 'jujuuser',
        'pubkey' : get_or_create_ssh_key()
    }]
    rspec = rspec_utils.create_rspec(nodes, userkeys, public_ipv4)
    env_conf = init_environment_config(env_name, rspec=rspec)
    create_virtualwall(env_name, env_conf, jfed)
    env_conf['locked'] = 'False'
    env_conf.save()
    create_juju(env_conf)


def configure_environment(_env_name):
    """ Run user-feedback-based initial config """
    env_conf = Config(DEFAULT_ENV_CONF, env_conf_path(_env_name))
    initial_config(env_conf)


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
        print "removing juju environment from juju config files"
        with open(expanduser("~/.juju/environments.yaml"), 'r') as config_file:
            config = yaml.load(config_file)
        if config['environments'] is not None:
            config['environments'].pop(name, None)
        with open(expanduser("~/.juju/environments.yaml"), 'w') as config_file:
            config_file.write(yaml.dump(config, default_flow_style=False))
        print "removing juju environment from juju environment folder"
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


def show_status(_env_name):
    jfed = init_jfed(_env_name, init_global_config())
    print "status of slice {} is {}".format(_env_name, jfed.get_status())


def show_info(_env_name):
    jfed = init_jfed(_env_name, init_global_config())
    info = jfed.get_sliceinfo()
    print "info of slice {}".format(_env_name)
    print "slice Expiration date: {}".format(info['sliceExpiration'])
    print "slice urn date: {}".format(info['sliceUrn'])
    print "user urn date: {}".format(info['userUrn'])
    print "speaksfor?: {}".format(info['usedSpeaksfor'])


def destroy_jfed_exp(_env_name):
    global_conf = init_global_config()
    env_conf = init_environment_config(_env_name)
    jfed = init_jfed(_env_name, global_conf, locked=env_conf['locked'])
    jfed.delete()
    print "Slice deleted"


def initial_config(config):
    """ asks environment config """
    def ask_value(question, default):
        """ Question helper: Ask question, show default, return default if
        answer == empty string"""
        print okblue(question)
        if default is not None:
            print "\tDefault: %s (press enter for default)" % default
        user_input = raw_input()
        if default is not None and (not user_input or user_input.isspace()):
            user_input = default
            print default
        print
        return user_input

    config['juju_env_conf']['bootstrap-user'] = ask_value( \
            "What is your username?\n\t(The username of your emulab account)",
            config['juju_env_conf'].get('bootstrap-user'))

    config['project_name'] = ask_value( \
            "What is your jFed/emulab project name?",
            config.get('project_name'))

    while True:
        user_input = ask_value(
            "What is the location of you emulab .PEM keyfile?"\
            "\n\tThis file is used to connect to jFed and the Virtual Wall "
            "servers. Please enter the absolute location"
            , config.get('key_path'))
        if os.path.isfile(user_input):
            with open(user_input, "r") as key_file:
                text = key_file.read()
            if text.startswith("-----BEGIN RSA PRIVATE KEY-----"):
                break
            else:
                print fail("ERROR: The given file is not a keyfile.")\
                      + "\nPlease specify the correct keyfile."
        else:
            print fail(
                "ERROR: could not find .PEM keyfile at this location.")\
                + "\nPlease enter the absolute location."
    config['key_path'] = user_input

    config['password'] = ask_value( \
                "What is the Password of your emulab keyfile?\n\t"\
                "This is the password you use to login to jFed."\
                "\n\tNote: this password will be stored plaintext in ~/.tengu",
                config.get('password'))

    config.save()

def show_userinfo():
    global_conf = init_global_config()
    jfed = init_bare_jfed(global_conf)
    print jfed.get_userinfo()


def downloadbigfiles(path):
    """Downloads url from .source files it finds in path"""
    # The top argument for walk
    topdir = os.path.realpath(path)
    print "downloading sources in %s " % topdir
    # The extension to search for
    exten = '.source'
    for dirpath, dirnames, files in os.walk(topdir):
        for name in files:
            if name.lower().endswith(exten):
                source = os.path.join(dirpath, name)
                file_to_download = source[:-len(exten)]
                print '%s' % file_to_download

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
                        print '\t DOWNLOADING FROM: %s' % url
                        urlopener = urllib.URLopener()
                        urlopener.retrieve(url, file_to_download)
                        if command == "extract":
                            print '\t EXTRACTING: %s' % file_to_download
                            tfile = tarfile.open(file_to_download, 'r')
                            # Important to note that the following extraction is
                            # UNSAFE since .tar.gz archive could contain
                            # relative path like ../../ and overwrite other dirs
                            tfile.extractall(os.path.dirname(file_to_download))
                else:
                    print '\t OK'
                print


WRONG_INPUT_MSG = """Usage:
tengu create <env-name> [<#nodes> [<#pub_ipv4>]]
tengu destroy <env-name>
tengu config <env-name>
tengu lock <env-name>
tengu unlock <env-name>
tengu jfed userinfo
tengu jfed status <env-name>
tengu jfed info <env-name>
tengu jfed create <env-name>
tengu jfed delete <env-name>
tengu jfed renew <env-name> <hours>
tengu juju create <env-name>
tengu juju add-machines <env-name>
tengu downloadbigfiles"""

def main():
    if len(sys.argv) == 2:
        if sys.argv[1] == "downloadbigfiles":
            downloadbigfiles('/opt/tengu-charms')
            return
    if len(sys.argv) == 3:
        if sys.argv[1] == "create":
            create_env(sys.argv[2])
            return
        elif sys.argv[1] == "destroy":
            destroy_environment(sys.argv[2])
            return
        elif sys.argv[1] == "config":
            configure_environment(sys.argv[2])
            return
        elif sys.argv[1] == "lock":
            lock_environment(sys.argv[2], True)
            return
        elif sys.argv[1] == "unlock":
            lock_environment(sys.argv[2], False)
            return
        elif sys.argv[1] == "jfed" and sys.argv[2] == 'userinfo':
            show_userinfo()
            return
    elif len(sys.argv) == 4:
        if sys.argv[1] == "create":
            create_env(sys.argv[2], sys.argv[3])
            return
        if sys.argv[1] == "jfed" and sys.argv[2] == "status":
            show_status(sys.argv[3])
            return
        if sys.argv[1] == "jfed" and sys.argv[2] == "info":
            show_info(sys.argv[3])
            return
        elif sys.argv[1] == "jfed" and sys.argv[2] == "delete":
            destroy_jfed_exp(sys.argv[3])
            return
        elif sys.argv[1] == "jfed" and sys.argv[2] == "create":
            global_conf = init_global_config()
            jfed = init_jfed(sys.argv[3], global_conf)
            env_conf = init_environment_config(sys.argv[3])
            create_virtualwall(sys.argv[3], env_conf, jfed)
            return
        elif sys.argv[1] == "juju" and sys.argv[2] == "create":
            global_conf = init_global_config()
            env_conf = init_environment_config(sys.argv[3])
            create_juju(env_conf)
            return
        elif sys.argv[1] == "juju" and sys.argv[2] == "export":
            global_conf = init_global_config()
            env_conf = init_environment_config(sys.argv[3])
            return
        elif sys.argv[1] == "juju" and sys.argv[2] == "add-machines":
            global_conf = init_global_config()
            env_conf = init_environment_config(sys.argv[3])
            machines = rspec_utils.get_machines(env_conf['manifest_path'])
            machines.pop(0)
            jujuenv = JujuEnvironment(sys.argv[3])
            jujuenv.add_machines(machines)
            return
    elif len(sys.argv) == 5:
        if sys.argv[1] == "create":
            create_env(sys.argv[2], sys.argv[3], sys.argv[4])
            return
        if sys.argv[1] == "jfed" and sys.argv[2] == "renew":
            slicename = sys.argv[3]
            hours = sys.argv[4]
            okwhite('renewing slice {} for {} hours'.format(slicename, hours))
            global_conf = init_global_config()
            jfed = init_jfed(slicename, global_conf)
            try:
                jfed.renew(hours)
            except Exception as ex:
                fail('renewing slice failed', ex)
            return
    print WRONG_INPUT_MSG


if __name__ == '__main__':
    main()
