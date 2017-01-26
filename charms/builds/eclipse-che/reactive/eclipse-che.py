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
from time import sleep
from subprocess import check_output, check_call, CalledProcessError

import requests
from requests.exceptions import ConnectionError
from charmhelpers.core.hookenv import (
    status_set,
    open_port,
    unit_public_ip,
)

from charms.reactive import set_state, when, when_not


@when("docker.available")
@when_not("che.available")
def run_che():
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
        'start'], universal_newlines=True).rstrip()
    wait_until_che_running()
    try:
        check_call(['docker', 'kill', container_id])
    except CalledProcessError:
        # container has already stopped
        pass
    check_call(['docker', 'rm', container_id])
    set_state('che.available')
    status_set('active', 'Ready')
    # opened ports are used by `juju expose` so It's important to open all
    # ports a user connects to.
    open_port('8080', protocol="TCP")           # Port to the UI
    open_port('32768-65535', protocol="TCP")    # Ports to the workspaces


def wait_until_che_running():
    print('Waiting for che to come online.. This might take a few minutes.')
    while True:
        try:
            response = requests.get('http://localhost:8080')
            if response.status_code == 200:
                break
        except ConnectionError as err:
            print(err)
        sleep(1)
    print('Che is online!')


def stop_che():
    check_call([
        'docker', 'run',
        '-it',
        '--rm',
        '-v', '/var/run/docker.sock:/var/run/docker.sock',
        '-v', '/home/ubuntu/:/data',
        '-e', 'CHE_HOST={}'.format(unit_public_ip()),
        '-e', 'CHE_DOCKER_IP_EXTERNAL={}'.format(unit_public_ip()),
        'eclipse/che',
        'stop'])
