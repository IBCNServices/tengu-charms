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
# pylint: disable=c0111,c0103,c0301

from charmhelpers.core import hookenv
from charms.reactive import when_not, set_state

import openjdk
import oracle


@when_not('java.installed')
def install():
    conf = hookenv.config()
    if conf['java-flavor'] == 'openjdk':
        openjdk.installopenjdk()
    elif conf['java-flavor'] == 'oracle':
        oracle.installoracle()
    else:
        openjdk.installopenjdk()
    set_state('java.installed')
