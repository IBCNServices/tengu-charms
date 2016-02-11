#!/usr/bin/python
# pylint: disable=c0411
""" Juju Hooks"""
import setup
setup.pre_install()
import sys
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port
from charmhelpers.core.hookenv import relation_set
import subprocess
import tarfile
import base64
#from lxml import etree
#from lxml.builder import E
import os
# Own modules
from confighelpers import mergecopytree

# Hooks
HOOKS = hookenv.Hooks()

@HOOKS.hook('upgrade-charm')
def upgrade():
    """Upgrade hook"""
    print "upgrading charm"
    try:
        subprocess.check_output(['sudo', 'service', 'rest2jfed', 'stop'])
    except subprocess.CalledProcessError as exception:
        print exception.output
        # we do not need to exit here
    install()


@HOOKS.hook('install')
def install():
    """Install hook"""
    try:
        # update needed because of weird error
        print "installing dependencies"
        subprocess.check_output(['sudo', 'apt-get', 'update'])
        # subprocess.check_output(['sudo', 'apt-get', '-y',
        #                          'install', 'maven'])
        # subprocess.check_output(['sudo', 'apt-get', '-y',
        #                          'install', 'openjdk-7-jre-headless'])
    except subprocess.CalledProcessError as exception:
        print exception.output
        exit(1)
    # proxy_obj = get_proxy()
    # if proxy_obj['proxy']:
    #     print "configuring maven proxy"
    #     host = proxy_obj['proxy'].split('://')[1]
    #     p_hostname = host.split(':')[0]
    #     p_port = host.split(':')[1]
    #     p_no_proxy = proxy_obj['no_proxy']
    #     add_maven_proxy(p_hostname, p_port, p_no_proxy)
    print "extracting and moving required files and folders"
    mergecopytree(charm_dir() + '/files/jfedS4', "/opt/jfedS4")
    mergecopytree(charm_dir() + '/files/rest2jfed', "/opt/rest2jfed")
    if not os.path.isdir('/opt/java/jre1.8.0_45'):
        tfile = tarfile.open(\
            charm_dir() + '/files/server-jre-8u45-linux-x64.tar.gz', 'r')
        # Important to note that the following extraction is
        # UNSAFE since .tar.gz archive could contain
        # relative path like ../../ and overwrite other dirs
        tfile.extractall(charm_dir() + '/files/')
        mergecopytree(charm_dir() + '/files/jdk1.8.0_45',
                      "/opt/java/jre1.8.0_45")
    # print "Building maven project cliREST"
    # try:
    #     subprocess.check_output(['mvn',
    #                              '-f', '/opt/rest2cli/cliREST/pom.xml',
    #                              'dependency:build-classpath',
    #                              '-Dmdep.outputFile=/opt/rest2cli/classpath'])
    # except subprocess.CalledProcessError as exception:
    #     print exception.output
    #     exit(1)
    # with open("/opt/rest2cli/classpath", 'r') as classpathfile:
    #     classpath = classpathfile.read().rstrip()
    print "Generating upstart file"
    with open(charm_dir()+'/templates/upstart.conf', 'r') as upstart_t_file:
        upstart_template = upstart_t_file.read()
    #upstart_template = upstart_template.replace('{{classpath}}', classpath)
    with open('/etc/init/rest2jfed.conf', 'w') as upstart_file:
        upstart_file = upstart_file.write(upstart_template)
    print "Starting rest2jfed service"
    try:
        subprocess.check_output(['sudo', 'service', 'rest2jfed', 'start'])
    except subprocess.CalledProcessError as exception:
        print exception.output
        exit(1)
    open_port(5000)


@HOOKS.hook('config-changed')
def config_changed():
    """Config changed"""
    hookenv.log('reconfiguring rest2jfed')
    conf = hookenv.config()
    with open('/opt/jfedS4/tengujfed.pass', 'w+') as pass_file:
        pass_file.write(conf['emulab-cert-pass'])
        pass_file.truncate()
    with open('/opt/jfedS4/tengujfed.pem', 'w+') as pemfile:
        pemfile.write(base64.b64decode(conf['emulab-cert']))
        pemfile.truncate()


@HOOKS.hook('rest2jfed-relation-changed')
def rest2jfed_relation_changed():
    """ Sets hostname and port on relation """
    hookenv.log('reconfiguring rest2jfed relation')
    host = hookenv.unit_public_ip()
    port = '5000'
    relation_set(host=host)
    relation_set(port=port)


# def add_maven_proxy(p_hostname, p_port, p_noproxy):
#     """ Adds proxy config to maven config file if not exists """
#     xml_filepath = '/usr/share/maven/conf/settings.xml'
#     # remove non-data whitespace so pretty_print will work
#     # keep comments
#     parser = etree.XMLParser(remove_blank_text=True, remove_comments=False)
#     tree = etree.parse(xml_filepath, parser)
#     root = tree.getroot()
#     # Check if proxy already exists
#     proxies_el = root.find('{http://maven.apache.org/SETTINGS/1.0.0}proxies')
#    proxy_el = proxies_el.find('{http://maven.apache.org/SETTINGS/1.0.0}proxy')
#     if proxy_el is None:
#         proxy_el = E.proxy(E.active('true'),
#                            E.protocol('http'),
#                            E.host(p_hostname),
#                            E.port(p_port),
#                            E.nonProxyHosts(p_noproxy))
#         proxies_el.append(proxy_el)
#     with open(xml_filepath, 'w') as outfile:
#         # pretty-print, add declaration and utf-8 encoding to make it resemble
#         # the original as much as possible,
#         tree.write(outfile,
#                    pretty_print=True,
#                    xml_declaration=True,
#                    encoding='UTF-8')

# Hook logic
if __name__ == "__main__":
    HOOKS.execute(sys.argv)
