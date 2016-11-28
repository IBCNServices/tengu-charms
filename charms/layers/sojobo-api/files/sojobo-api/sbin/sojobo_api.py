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
from os.path import dirname, realpath
import socket
import shutil
from shutil import copy2
import tempfile
from subprocess import check_call, check_output
from distutils.util import strtobool

from flask import Flask, request, redirect, send_file
from helpers import write_yaml, create_response, authenticate, get_controllers
from juju import JUJU_USER, JUJU_PASSWORD, CONTROLLER_NAME, CLOUD_NAME, juju_get_gui_url, juju_create_model
from juju import juju_status, juju_config
from controllers.maas import MAAS_USER, MAAS_URL, MAAS_API_KEY
#
# Init feature flags and global variables
#
# Docs:
# - https://flask-featureflags.readthedocs.io/en/latest/
# - http://groovematic.com/2014/10/feature-flags-in-flask/
# - http://zurb.com/forrst/posts/Feature_Flags_in_python-ulC
#
def parse_flags_from_environment(flags):
    """Creates a global bool variable for each name in `flags`.
    The value of the global variable is
     - `True` if an environment variable with the same name exists and is interpreted as True (by strtobool(value.lower())).
     - `False` in any other case
    """
    for flagname in flags:
        value = False
        try:
            value = strtobool(os.environ.get(flagname, 'False').lower())
        except ValueError:
            pass
        globals()[flagname] = value


DEBUG = False
parse_flags_from_environment(['DEBUG', 'FEATURE_FLAG_AUTH'])
#
# Init flask
#
APP = Flask(__name__)
APP.url_map.strict_slashes = False
#
# schedule periodic re-login
#
def login():
    print("'LOGIN' START")
    check_call(['maas', 'login', MAAS_USER, MAAS_URL, MAAS_API_KEY])
    print(check_output(
        ['juju', 'login', JUJU_USER, '--controller', CONTROLLER_NAME],
        input=JUJU_PASSWORD + '\n',
        universal_newlines=True))
    print("'LOGIN' FINISHED")


@APP.before_request
def initialize():
    login()


@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authentication,Content-Type,Location,id-token'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT'
    response.headers['Accept'] = 'application/json'
    return response


@APP.errorhandler(403)
def forbidden(e):
    return create_response(403, {'message': e.description['message']})
#
# Controllers
#
@APP.route('/')
def api_root():
    """ Welcome message """
    info = {
        "name": socket.gethostname(),
        "version": "0.0.1", # see http://semver.org/
    }
    return create_response(200, info)


@APP.route('/favicon.ico')
def api_icon():
    """ icon """
    return redirect("http://tengu.io/assets/icons/favicon.ico", code=302)


@APP.route('/users/<username>', methods=['GET', 'PUT'])
def create_user(username):
    token = authenticate(request.authorization, username)
    response = {
        'gui-url': juju_get_gui_url(token)
    }
    return create_response(200, response)


@APP.route('/users/<username>/models/<modelname>', methods=['GET', 'PUT'])
def create_model(username, modelname):
    token = authenticate(request.authorization, username, modelname)
    if request.method == 'PUT':
        model = request.json
        juju_create_model(token.username, token.api_key, model['ssh-keys'], token.modelname)
    response = {
        'model-realname': token.modelname,
        'model-prettyname': modelname,
        'gui-url': juju_get_gui_url(token),
    }
    return create_response(200, response)


@APP.route('/users/<username>/models/<modelname>/status', methods=['GET'])
def status(username, modelname):
    token = authenticate(request.authorization, username, modelname)
    response = juju_status(token)
    return create_response(200, response)


@APP.route('/users/<username>/models/<modelname>/applications/<appname>/config', methods=['GET'])
def get_config(username, modelname, appname):
    token = authenticate(request.authorization, username, modelname)
    response = juju_config(token, appname)
    return create_response(200, response)


@APP.route('/users/<username>/credentials.zip', methods=['GET'])
def get_credentials(username):
    token = authenticate(request.authorization, username)
    credentials = {
        'credentials': {
            CLOUD_NAME: {
                token.username: {
                    'auth-type': 'oauth1',
                    'maas-oauth': token.api_key,
                }
            }
        }
    }
    clouds = {
        'clouds':{
            CLOUD_NAME: {
                'type': 'maas',
                'auth-types': ['oauth1'],
                'endpoint': MAAS_URL,
            }
        }
    }
    controllers = get_controllers(CONTROLLER_NAME)
    tmpdir = tempfile.mkdtemp()
    os.mkdir('{}/creds'.format(tmpdir))
    write_yaml('{}/creds/clouds.yaml'.format(tmpdir), clouds)
    write_yaml('{}/creds/credentials.yaml'.format(tmpdir), credentials)
    write_yaml('{}/creds/controllers.yaml'.format(tmpdir), controllers)
    copy2("{}/install_credentials.py".format(dirname(realpath(__file__))), '{}/creds/install_credentials.py'.format(tmpdir))
    shutil.make_archive('{}/creds'.format(tmpdir), 'zip', '{}/creds/'.format(tmpdir))
    return send_file('{}/creds.zip'.format(tmpdir))
#
# Run flask server when file is executed
#
if __name__ == '__main__':
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
