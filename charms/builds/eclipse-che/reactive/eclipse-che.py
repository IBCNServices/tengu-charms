#!/usr/bin/env python3
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
import json
from shutil import copyfile
from time import sleep
from subprocess import check_output, check_call, CalledProcessError

import requests
from charmhelpers.core.hookenv import (
    status_set,
    open_port,
    unit_public_ip,
    charm_dir,
)

from charms.reactive import set_state, when, when_not


@when("docker.available")
@when_not("che.available")
def run_che():
    status_set('maintenance', 'Installing Eclipse Che')
    # Start and stop Che so che's config is generated
    start_che()
    stop_che()
    # Add Juju stuff to Che config
    json_add_object_to_array(
        "{}/templates/stack-juju-charm.json".format(charm_dir()),
        "/home/ubuntu/instance/data/stacks/stacks.json"
    )
    copyfile(
        "{}/templates/type-juju.svg".format(charm_dir()),
        "/home/ubuntu/instance/data/stacks/images/type-juju.svg"
    )
    json_add_object_to_array(
        "{}/templates/project-template-charms.json".format(charm_dir()),
        "/home/ubuntu/instance/data/templates/samples.json"
    )
    json_add_object_to_array(
        "{}/templates/project-template-interface.json".format(charm_dir()),
        "/home/ubuntu/instance/data/templates/samples.json"
    )
    json_add_object_to_array(
        "{}/templates/project-template-layer.json".format(charm_dir()),
        "/home/ubuntu/instance/data/templates/samples.json"
    )
    # Start Che for real
    start_che()
    # opened ports are used by `juju expose` so It's important to open all
    # ports a user connects to.
    open_port('8080', protocol="TCP")           # Port to the UI
    open_port('32768-65535', protocol="TCP")    # Ports to the workspaces
    status_set('active', 'Ready')
    set_state('che.available')


@when('editor.available', 'che.available')
def configure_http_relation(editor_relation):
    editor_relation.configure(port=8080)


def wait_until_che_running():
    print('Waiting for che to come online.. This might take a few minutes.')
    while True:
        try:
            response = requests.get('http://localhost:8080')
            if response.status_code == 200:
                break
        except (requests.exceptions.ConnectionError) as err:
            print(err)
            print("retrying..")
        sleep(1)
    print('Che is online!')


def start_che():
    # This container isn't Che. This container starts Che. This should be run
    # in interactive mode, but this container waits until it can reach che on
    # its public_ip. On a public cloud, public_ip might only be accessible
    # after running `juju expose`, so this might never exit. Because of this
    # reason, we run the container in daemon mode, check che's status ourselves
    # and kill the container manually after Che is up.
    container_id = check_output([
        'docker', 'run',
        '-itd',
        '-v', '/var/run/docker.sock:/var/run/docker.sock',
        '-v', '/home/ubuntu/:/data',
        '-e', 'CHE_HOST={}'.format(unit_public_ip()),
        '-e', 'CHE_DOCKER_IP_EXTERNAL={}'.format(unit_public_ip()),
        'eclipse/che',
        'start',
        '--fast'], universal_newlines=True).rstrip()
    wait_until_che_running()
    try:
        check_call(['docker', 'kill', container_id])
    except CalledProcessError:
        # container has already stopped
        print("Killing startup container failed")
    check_call(['docker', 'rm', container_id])


def stop_che():
    try:
        check_call([
            'docker', 'run',
            '-it',
            '--rm',
            '-v', '/var/run/docker.sock:/var/run/docker.sock',
            '-v', '/home/ubuntu/:/data',
            '-e', 'CHE_HOST={}'.format(unit_public_ip()),
            '-e', 'CHE_DOCKER_IP_EXTERNAL={}'.format(unit_public_ip()),
            'eclipse/che',  # :5.1.2
            'stop'])
    except CalledProcessError:
        print("Stopping Che failed")


def json_add_object_to_array(object_path, array_path):
    with open(object_path, 'r') as object_file:
        patch = json.loads(object_file.read())
    with open(array_path, 'r+') as array_file:
        samples = json.loads(array_file.read())
        samples.append(patch)
        array_file.seek(0)
        array_file.write(json.dumps(samples, indent=4))
        array_file.truncate()


# def create_juju_stack():
#     stackpath = "{}/templates/juju-charm-stack.json".format(charm_dir())
#     with open(stackpath, 'r') as stackfile:
#         stack = stackfile.read()
#     response = requests.post('http://localhost:8080/api/stack', data=stack)
#     if response.status_code not in (401, 409):
#         print("Creating stack failed!", response.text())
#         exit(1)
#     print(response.text())
