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


ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
URL = os.environ.get('AWS_URL')

def get_credentials(username):
    return {'aws': {username, {'auth-type': 'access-key', 'access-key': ACCESS_KEY, 'secret-key': SECRET_KEY}}}


def get_clouds(cloud):
    return {'clouds':{cloud: {'type': 'aws', 'auth-types': ['access-key'], 'endpoint': URL}}}
