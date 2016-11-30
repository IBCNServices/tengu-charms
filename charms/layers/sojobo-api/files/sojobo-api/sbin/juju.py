# !/usr/bin/env python3
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
# pylint: disable=c0111,c0301,c0325,c0103
import os
import json
import tempfile
from subprocess import check_call, check_output, STDOUT, CalledProcessError
from controllers import maas, aws
from helpers import Token


USER = os.environ.get('JUJU_USER')
PASSWORD = os.environ.get('JUJU_PASSWORD')
CONTROLLER_TYPE = os.environ.get('CONTROLLER_TYPE')
CONTROLLER_NAME = os.environ.get('CONTROLLER_NAME')
CLOUD_NAME = "{}-{}".format(CONTROLLER_TYPE, CONTROLLER_NAME)


def list_users():
    users = json.loads(check_output(['juju', 'list-users', '--format', 'json'],
                                    universal_newlines=True))
    return [u['user-name'] for u in users]


def create_user(username, password):
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


def create_model(token, ssh_keys):
    if CONTROLLER_TYPE == 'maas':
        credentials = maas.get_credentials(CLOUD_NAME, token.username, token.api_key)
    else:
        credentials = aws.get_credentials(token.username)
    tmp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    tmp.write(json.dumps(credentials))
    tmp.close()  # deletes the file
    modelconfig = []
    if ssh_keys:
        modelconfig = modelconfig + ['authorized-keys="{}"'.format(ssh_keys)]
    if len(modelconfig):
        modelconfig = ['--config'] + modelconfig
    check_call(['juju', 'add-credential', '--replace', CLOUD_NAME, '-f', tmp.name])
    check_call(['juju', 'add-model', token.modelname, '--credential', token.username] + modelconfig)
    check_call(['juju', 'grant', token.username, 'admin', token.modelname])


def get_gui_url(token):
    modelname = 'controller'
    if token.modelname:
        modelname = token.modelname
    return check_output(['juju', 'gui', '--no-browser', '--model', modelname], universal_newlines=True, stderr=STDOUT).rstrip()


def status(token):
    output = check_output(['juju', 'status', '--format', 'json', '--model', token.modelname], universal_newlines=True)
    return json.loads(output)


def config(token, appname):
    output = check_output(['juju', 'config', appname, '--model', token.modelname, '--format', 'json'], universal_newlines=True)
    return json.loads(output)


def authenticate(auth, modelname=None):
    check_output(['juju', 'login', USER, '--controller', CONTROLLER_NAME], input=PASSWORD + '\n',
                 universal_newlines=True)
    if not user_exists(auth.username, modelname):
        create_user(auth.username, auth.password)
    token = Token(auth.username, auth.password)
    if CONTROLLER_TYPE == 'maas':
        check_call(['maas', 'login', maas.USER, maas.URL, maas.API_KEY])
        if not auth.username in maas.list_users():
            maas.create_user(auth.username, auth.password)
        token.api_key = maas.get_user_api_key(token.username, auth.password)
    if modelname:
        token.modelname = "{}-{}".format(auth.username, modelname)
        token.fqmodelname = "admin/{}".format(token.modelname)
    return token


def user_exists(username, modelname=None):
    exists = False
    if modelname:
        output = check_output(['juju', 'users', modelname, '--format', 'json'])
        if username in json.loads(output[:-1]):
            exists = True
    else:
        output = check_output(['juju', 'users', '--format', 'json'])
        if username in json.loads(output[1:-2]).values():
            exists = True
    return exists


def model_exists(token):
    exists = False
    data = json.loads(check_output(['juju', 'list-models', '--format', 'json']))
    for model in data['models']:
        if token.modelname == model['name']:
            exists = True
            break
    return exists


def get_credentials(token):
    if CONTROLLER_TYPE == "maas":
        credentials = maas.get_credentials(CLOUD_NAME, token.username, token.api_key)
    else:
        credentials = aws.get_credentials(token.username)
    return credentials


def get_clouds():
    if CONTROLLER_TYPE == "maas":
        clouds = maas.get_clouds(CLOUD_NAME)
    else:
        clouds = aws.get_clouds(CLOUD_NAME)
    return clouds
