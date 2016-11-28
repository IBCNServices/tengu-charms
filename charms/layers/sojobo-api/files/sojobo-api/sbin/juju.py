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
# pylint: disable=c0111,c0301,c0325
# !/usr/bin/env python3 -- before upload to github, prepend file
import os
import json
import tempfile
from subprocess import check_call, check_output, STDOUT, CalledProcessError


JUJU_USER = os.environ.get('JUJU_USER')
JUJU_PASSWORD = os.environ.get('JUJU_PASSWORD')
CONTROLLER_NAME = os.environ.get('CONTROLLER_NAME')
CLOUD_NAME = "tengumaas"


def juju_list_users():
    users = json.loads(check_output(['juju', 'list-users', '--format', 'json'],
                                    universal_newlines=True))
    return [u['user-name'] for u in users]


def juju_create_user(username, password):
    check_call(['juju', 'add-user', username])
    check_call(['juju', 'grant', username, 'add-model'])
    output = None
    try:
        # We need to use check_output here because check_call has no "input" option
        output = check_output(['juju', 'change-user-password', username],
                              input="{}\n{}".format(password, password),
                              universal_newlines=True)
    except CalledProcessError as e:
        output = e.output
    finally:
        print(output)


def juju_create_model(username, api_key, ssh_keys, modelname):
    credentials = {
        'credentials': {
            CLOUD_NAME: {
                username: {
                    'auth-type': 'oauth1',
                    'maas-oauth': api_key,
                }
            }
        }
    }
    tmp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    tmp.write(json.dumps(credentials))
    tmp.close()  # deletes the file
    modelconfig = []
    if ssh_keys:
        modelconfig = modelconfig + ['authorized-keys="{}"'.format(ssh_keys)]
    if len(modelconfig):
        modelconfig = ['--config'] + modelconfig
    check_call(['juju', 'add-credential', '--replace', CLOUD_NAME, '-f', tmp.name])
    check_call(['juju', 'add-model', modelname, '--credential', username] + modelconfig)
    check_call(['juju', 'grant', username, 'admin', modelname])


def juju_get_gui_url(token):
    modelname = 'controller'
    if token.modelname:
        modelname = token.modelname
    return check_output(['juju', 'gui', '--no-browser', '--model', modelname], universal_newlines=True, stderr=STDOUT).rstrip()


def juju_status(token):
    output = check_output(['juju', 'status', '--format', 'json', '--model', token.modelname], universal_newlines=True)
    return json.loads(output)


def juju_config(token, appname):
    output = check_output(['juju', 'config', appname, '--model', token.modelname, '--format', 'json'], universal_newlines=True)
    return json.loads(output)
