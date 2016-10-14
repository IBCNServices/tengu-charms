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
#pylint: disable=c0111,c0103
# maas login galgalesh http://193.190.127.150/MAAS/api/1.9/
import os
import subprocess

from flask import Flask, request, Response


APP = Flask(__name__)

@APP.route("/")
def hello():
    return "REST to MAAS v0.0.1"

@APP.route("/keys/", methods=['POST'])
def POST_topic(topic):
    if not user_exists(username):
        create_user(username)
    return Response(
        "User created. API key is: {}".format(api_key),
        status=200,
        mimetype='text/plain',
    )


def user_exists(username):
    return os.path.isfile('/opt/rest2maas/{}'.format(username))


def create_user(user):
    email = get_username()
    subprocess.check_call(['maas', 'galgalesh', 'users', 'create', 'username={}'.format(username), 'email={}'.format(email), 'password={}'.format(password), 'is_superuser=1'])

def create_api_key(username):
    with open('/opt/rest2maas/{}'.format(username)) as passwdfile:
        password = passwdfile.read()
    subprocess.check_call(['maas', 'galgalesh', 'users', 'create', 'username={}'.format(username), 'email={}'.format(email), 'password={}'.format(password), 'is_superuser=1'])
    pass

if __name__ == "__main__":
    DEBUG = (os.environ.get('DEBUG', 'False').lower() == 'true')
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
