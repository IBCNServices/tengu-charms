#!/bin/bash
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
#sudo pip2 install click pyyaml
#echo '/opt/tengu/scripts/tengu.py "$@"' | sudo tee /usr/bin/tengu
#sudo chmod a+x /usr/bin/tengu
sudo cp -r /opt/tengu/scripts /opt/tengu/scripts.bak`date "+%y-%d-%m_%H:%M:%S"`
sudo rm -r /opt/tengu/scripts/*
sudo cp -r . /opt/tengu/scripts/
