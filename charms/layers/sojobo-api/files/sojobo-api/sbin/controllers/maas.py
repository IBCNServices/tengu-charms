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
import json
from subprocess import check_call, check_output

from lxml import html
import requests


USER = os.environ.get('MAAS_USER')
PASSWORD = os.environ.get('MAAS_PASSWORD')
API_KEY = os.environ.get('MAAS_API_KEY')
URL = os.environ.get('MAAS_URL')


def list_users():
    users = json.loads(check_output(['maas', USER, 'users', 'read'], universal_newlines=True))
    return [u['username'] for u in users]


def create_user(username, password):
    # email has to be unique
    check_call(['maas', USER, 'users', 'create', 'username={}'.format(username), 'email=merlijn.sebrechts+maas-user-{}@gmail.com'.format(username), 'password={}'.format(password), 'is_superuser=0'])


def get_user_api_key(username, password):
    # source: https://stackoverflow.com/questions/11892729/how-to-log-in-to-a-website-using-pythons-requests-module/17633072#17633072
    payload = {
        'username': username,
        'password': password
    }
    with requests.Session() as session:
        login_response = session.post('http://193.190.127.161/MAAS/accounts/login/', data=payload)
        print(login_response)
        api_page_response = session.get('http://193.190.127.161/MAAS/account/prefs/')
        print(api_page_response)
    tree = html.fromstring(api_page_response.text)
    api_keys = tree.xpath('//div[@id="api"]//input/@value')
    return str(api_keys[-1])


def get_credentials(cloud, username, api_key):
    return {'credentials': {cloud: {username: {'auth-type': 'oauth1', 'maas-oauth': api_key}}}}


def get_clouds(cloud):
    return {'clouds':{cloud: {'type': 'maas', 'auth-types': ['oauth1'], 'endpoint': URL}}}
