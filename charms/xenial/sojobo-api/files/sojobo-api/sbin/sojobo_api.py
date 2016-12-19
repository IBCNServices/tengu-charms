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
# pylint: disable=c0111,c0301,c0325
import os
from os.path import expanduser, dirname, realpath
import json
import socket
import shutil
from shutil import copy2
import tempfile
from subprocess import check_call, check_output, STDOUT, CalledProcessError
from distutils.util import strtobool

from lxml import html
import requests
from pygments import highlight, lexers, formatters
from flask import Flask, Response, request, redirect, send_file
import yaml
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

MAAS_USER = os.environ.get('MAAS_USER')
MAAS_API_KEY = os.environ.get('MAAS_API_KEY')
MAAS_URL = os.environ.get('MAAS_URL')

JUJU_USER = os.environ.get('JUJU_USER')
JUJU_PASSWORD = os.environ.get('JUJU_PASSWORD')
CONTROLLER_NAME = os.environ.get('CONTROLLER_NAME')
CLOUD_NAME = "tengumaas"

#
# Init flask
#dev-sojobo-api/0
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

# @APP.errorhandler(JujuNotFoundException)
# def handle_invalid_usage(error):
#     return create_response(404, {"msg": 'Cannot find resource. Reason: {}'.format(error.message)})

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
    if not token:
        return create_response(403, {'message': "Auth failed! username in auth and in url have to be the same"})
    response = {
        'gui-url': juju_get_gui_url(token)
    }
    return create_response(200, response)


@APP.route('/users/<username>/models/<modelname>', methods=['GET', 'PUT'])
def create_model(username, modelname):
    token = authenticate(request.authorization, username, modelname)
    if not token:
        return create_response(403, {'message':"Auth failed! username in auth and in url have to be the same"})
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
    if not token:
        return create_response(403, {'message':"Auth failed! username in auth and in url have to be the same"})
    response = juju_status(token)
    return create_response(200, response)


@APP.route('/users/<username>/models/<modelname>/applications/<appname>/config', methods=['GET'])
def get_config(username, modelname, appname):
    token = authenticate(request.authorization, username, modelname)
    if not token:
        return create_response(403, {'message':"Auth failed! username in auth and in url have to be the same"})
    response = juju_config(token, appname)
    return create_response(200, response)


@APP.route('/users/<username>/credentials.zip', methods=['GET'])
def get_credentials(username):
    token = authenticate(request.authorization, username)
    if not token:
        return create_response(403, {'message':"Auth failed! username in auth and in url have to be the same"})
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


def write_yaml(path, content):
    with open(path, "w") as y_file:
        y_file.write(yaml.dump(content))

def authenticate(auth, username, modelname=None):
    if username != auth.username:
        return None
    if not auth.username in maas_list_users():
        maas_create_user(auth.username, auth.password)
        juju_create_user(auth.username, auth.password)
    token = Token()
    token.username = auth.username
    token.password = auth.password
    token.api_key = maas_get_user_api_key(token.username, auth.password)
    if modelname:
        token.modelname = "{}-{}".format(auth.username, modelname)
        token.fqmodelname = "admin/{}".format(token.modelname)
    return token

def maas_list_users():
    users = json.loads(check_output(['maas', MAAS_USER, 'users', 'read'], universal_newlines=True))
    return [u['username'] for u in users]

def maas_create_user(username, password):
    # email has to be unique
    check_call(['maas', MAAS_USER, 'users', 'create', 'username={}'.format(username), 'email=merlijn.sebrechts+maas-user-{}@gmail.com'.format(username), 'password={}'.format(password), 'is_superuser=0'])

def maas_get_user_api_key(username, password):
    # source: https://stackoverflow.com/questions/11892729/how-to-log-in-to-a-website-using-pythons-requests-module/17633072#17633072
    payload = {
        'username': username,
        'password': password
    }
    with requests.Session() as session:
        login_response = session.post('{}/accounts/login/'.format(MAAS_URL), data=payload)
        print(login_response)
        api_page_response = session.get('{}/account/prefs/'.format(MAAS_URL))
        print(api_page_response)
    tree = html.fromstring(api_page_response.text)
    api_keys = tree.xpath('//div[@id="api"]//input/@value')
    return str(api_keys[-1])

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
                              input="{}\n{}\n".format(password, password),
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


def get_controllers(name):
    with open(expanduser('~/.local/share/juju/controllers.yaml'))as c_file:
        c_contents = yaml.safe_load(c_file)
    return {
        'controllers': {
            name : c_contents['controllers'][name]
        }
    }

#
# Helpers
#
def create_response(http_code, return_object):
    if request_wants_json():
        return Response(
            json.dumps(return_object),
            status=http_code,
            mimetype='application/json',
        )
    else:
        formatted_json = json.dumps(return_object, indent=4)
        formatter = formatters.HtmlFormatter( #pylint: disable=E1101
            full=True,
            title="{} returns:".format(socket.gethostname())
        )
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatter) # pylint: disable=E1101
        return Response(
            colorful_json,
            status=http_code,
            mimetype='text/html',
        )


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

class Token(object):
    def __init__(self):
        self.username = None
        self.password = None
        self.api_key = None
        self.modelname = None
        self.fqmodelname = None
#
# Run flask server when file is executed
#
if __name__ == '__main__':
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
