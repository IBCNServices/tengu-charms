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
# pylint: disable=c0111,c0301,c0325
import os
from os.path import dirname, realpath
import socket
import shutil
from shutil import copy2
import tempfile
from distutils.util import strtobool

from flask import Flask, request, redirect, send_file
from helpers import write_yaml, create_response, get_controllers
import juju
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
@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authentication,Content-Type,Location,id-token'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    response.headers['Accept'] = 'application/json'
    return response


@APP.errorhandler(403)
def forbidden(error):
    return create_response(403, {'message': error.description['message']})
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


# Creating users using a post request with json data. This must be added to documentation of api
@APP.route('/users/create/', methods=['POST'])
def create_user():
    token = juju.authenticate(request.authorization)
    data = request.json
    if juju.user_exists(data['username']):
        response = {'message': 'The user already exists'}
    else:
        juju.create_user(data['username'], data['password'])
        response = {'gui-url': juju.get_gui_url(token)}
    return create_response(200, response)


# Creating models using a post request with json data. This must be added to documentation of api
@APP.route('/models/create', methods=['POST'])
def create_model():
    data = request.json
    token = juju.authenticate(request.authorization, data['modelname'])
    if juju.model_exists(token):
        response = {'message': 'The model already exists'}
    else:
        juju.create_model(token, data['ssh-keys'])
        response = {'model-name': token.modelname,
                    'model-fullname': token.fqmodelname,
                    'gui-url': juju.get_gui_url(token)}
    return create_response(200, response)


@APP.route('/models/<modelname>/status', methods=['GET'])
def status(modelname):
    token = juju.authenticate(request.authorization, modelname)
    response = juju.status(token)
    return create_response(200, response)


@APP.route('/models/<modelname>/applications/<appname>/config', methods=['GET'])
def get_config(modelname, appname):
    token = juju.authenticate(request.authorization, modelname)
    response = juju.config(token, appname)
    return create_response(200, response)


@APP.route('/users/credentials.zip', methods=['GET'])
def get_credentials():
    credentials = juju.get_credentials(juju.authenticate(request.authorization))
    clouds = juju.get_clouds()
    controllers = get_controllers(juju.CONTROLLER_NAME)
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
