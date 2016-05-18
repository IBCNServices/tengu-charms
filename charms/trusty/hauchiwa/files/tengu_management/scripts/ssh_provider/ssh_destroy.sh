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
sudo rm -rf /etc/init/juju*
sudo rm -rf /var/lib/juju
sudo pkill -f juju
sleep 5

sudo apt-get -y remove juju-mongodb landscape-common lxc
sudo apt-get -y autoremove
sudo rm -rf /var/lib/lxc/*
sudo pkill -f juju
sleep 5
sudo pkill -9 -f juju
sudo rm -rf /var/lib/juju
sudo rm -rf /usr/lib/juju /etc/rsyslog.d/25-juju.conf
sudo rm -rf /tmp/pprof.jujud.* /usr/bin/juju-run /home/ubuntu/.juju-proxy /etc/apt/apt.conf.d/42-juju-proxy-settings /var/log/upstart/juju-db.log /var/log/juju /var/log/lxc/ /var/log/upstart/lxc-instance-juju-machine-0-lxc-1.log
sudo rm -r /etc/juju
sudo rm -r /run/lxc/lock
sudo rm -rf /var/log/upstart/lxc*
sudo rm -rf /var/log/cloud-init-output.log


#
# juju destroy-machine 1 2 3 4
# sleep 5
# juju destroy-machine 1 2 3 4 --force
#
#sudo su -
#umount /var/lib/lxc
#rm -r /var/lib/lxc/*
#mount /var/lib/lxc/


# Lessons learned
# if ip is in ip link show; the juju will know about it, whether the link is on or not.
