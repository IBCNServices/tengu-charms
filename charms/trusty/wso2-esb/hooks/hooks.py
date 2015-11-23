#!/usr/bin/python
# pylint: disable=c0111
# pylint: disable=c0301
import setup #pylint: disable=F0401
setup.pre_install()
import sys
import os
import shutil
import subprocess
import pwd
import grp
import requests
import time

from charmhelpers.core import hookenv, templating
from charmhelpers.core.hookenv import Hooks, relation_get, log, charm_dir

from chefhelpers import install_chef_zero, \
                        configure_chef_zero, \
                        install_chef_cookbooks, \
                        run_recipe #pylint: disable=F0401


KAFKA_CONNECTOR_VERSION = "1.0.0"
ESB_VERSION = "4.9.0"
PING_SOAP_MESSAGE = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://www.w3.org/2003/05/soap-envelope">
   <soapenv:Body>
      <p:echoInt xmlns:p="http://echo.services.core.carbon.wso2.org">
         <in>1</in>
      </p:echoInt>
   </soapenv:Body>
</soapenv:Envelope>"""

HOOKS = Hooks()

@HOOKS.hook('install')
def install():
    # needed because of weird error
    subprocess.check_call(['sudo', 'apt-get', 'update'])
    install_chef_zero()
    configure_chef_zero()
    # copy cookbooks and upload to server
    install_chef_cookbooks()
    # run wso2 esb cookbook
    run_recipe("wso2::esb")
    # Wait for ESB to start
    counter = 0
    print "Waiting for ESB to come online"
    while not esb_is_online():
        if counter >= 10:
            raise Exception("esb takes to long to come online")
        counter += 1
        time.sleep(10)
    # mark ports as open
    hookenv.open_port('9443')            # https Management console
    hookenv.open_port('9763')            # http Management console
    hookenv.open_port('8280')            # WSDL and API/proxy
    hookenv.open_port('8243')            # API/proxy


@HOOKS.hook('kafka-relation-joined')
def client_relation_joined():
    install_kafka_connector()


@HOOKS.hook('hadoop-relation-changed')
def hadoop_relation_changed():
    log("hadoop-relation-changed")


def install_kafka_connector():
    server_path = "/opt/wso2esb/wso2esb-{}/repository/deployment/server".format(ESB_VERSION)

    # copy connector
    synapse_libs_path = '{}/synapse-libs'.format(server_path)
    if not os.path.exists(synapse_libs_path):
        os.makedirs(synapse_libs_path)
    shutil.copy(charm_dir() + '/files/kafka-connector-%s.zip' % KAFKA_CONNECTOR_VERSION, synapse_libs_path)
    os.chown(
        charm_dir() + '/files/kafka-connector-%s.zip' % KAFKA_CONNECTOR_VERSION,
        pwd.getpwnam("esbuser").pw_uid,
        grp.getgrnam("wso2").gr_gid
    )

    # enable connector
    kafka_enable_path = "{}/synapse-configs/default/imports/".format(server_path)
    if not os.path.exists(kafka_enable_path):
        os.makedirs(kafka_enable_path)
    templating.render(
        source='{org.wso2.carbon.connector}kafka.xml',
        target='%s/{org.wso2.carbon.connector}kafka.xml' % kafka_enable_path,
        context={},
        owner='esbuser',
        group='wso2',
    )
    # Wait for kafka connector to come online
    time.sleep(20)

    # Copy sequence
    kafka_hostname = relation_get('private-address')
    kafka_topic = "test"
    sequence_path = "{}/synapse-configs/default/sequences".format(server_path)
    if not os.path.exists(sequence_path):
        os.makedirs(sequence_path)
    templating.render(
        source='postTopic.xml',
        target='{}/postTopic.xml'.format('/opt/wso2-esb'),
        context={
            'kafka_broker': kafka_hostname,
            'kafka_topic': kafka_topic,
        },
        owner='esbuser',
        group='wso2',
    )
    shutil.move('/opt/wso2-esb/postTopic.xml', sequence_path + '/postTopic.xml')

    # Copy API
    api_path = "{}/synapse-configs/default/api".format(server_path)
    if not os.path.exists(api_path):
        os.makedirs(api_path)
    templating.render(
        source='kafka.xml',
        target='{}/kafka.xml'.format(api_path),
        context={},
        owner='esbuser',
        group='wso2',
    )


def copy_kafka_endpoint_libraries():
    """ Used for the official wso2 kafka connector """
    esb_home = "/opt/wso2esb/wso2esb-{}".format(ESB_VERSION)
    libs = [
        'kafka_2.10-0.8.2.1.jar',
        'scala-library-2.10.4.jar',
        'zkclient-0.3.jar',
        'zookeeper-3.4.6.jar',
        'metrics-core-2.2.0.jar',
        'kafka-clients-0.8.2.1.jar'
    ]
    for lib in libs:
        shutil.copy(charm_dir() + '/files/libs/' + lib, '{}/repository/components/lib'.format(esb_home))


def esb_is_online():
    soap_message = PING_SOAP_MESSAGE
    url = 'http://localhost:8280/services/echo'
    headers = {
        'Content-Type': 'application/soap+xml',
        'charset': 'UTF-8',
        'action': 'urn:echoInt'
    }
    try:
        response = requests.post(url, data=soap_message, headers=headers, verify=False)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        pass
    return False


if __name__ == "__main__":
    HOOKS.execute(sys.argv)
