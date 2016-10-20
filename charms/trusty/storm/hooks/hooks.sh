#!/bin/bash

set -e

private_address=`unit-get private-address` #TODO: this won't always return an ip address
version=`config-get version`

configure_hosts () {
	  set +e
		# This is a horrible hack to ensure that
		# Java can resolve the hostname of the server to its
		# real IP address.

		# Fixup stuff in lxc containers
		hostname=`hostname`
		grep -q "$private_address $hostname" /etc/hosts || echo "$private_address $hostname" >> /etc/hosts
		set -e
}

install_base_packages () {
	  juju-log "Installing storm..."
		juju-log "installing python charm helpers"
		apt-get install -y python-pip python-yaml
		pip install charmhelpers
		juju-log "Setting app directory"
		juju-log $CHARM_DIR
		juju-log "Installing the dependencies for nimbus - jdk 6, python 2.6, unzip"
		apt-get install -y python
		apt-get install -y unzip
		if [ "$version" = "0.10.0" ]; then
		  apt-get install -y openjdk-7-jdk
		else
			apt-get install -y openjdk-6-jdk
		fi
		apt-get install -y maven
		apt-get install -y daemon
		juju-log "Installing the dependencies for nimbus - storm ${version}"
		groupadd -f storm
		id -u storm &>/dev/null || useradd -g storm storm
		wget -nc http://www.mirrorservice.org/sites/ftp.apache.org/storm/apache-storm-${version}/apache-storm-${version}.zip
		sha512sum -c $CHARM_DIR/apache-storm-${version}.zip.sha
		unzip -u $CHARM_DIR/apache-storm-${version}.zip
		mkdir -p /opt/storm
		cp -u -r $CHARM_DIR/apache-storm-${version} /opt/storm/
		chown -R storm:storm  /opt/storm/
		install -C $CHARM_DIR/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tpl -g storm -o storm
		ln -snf /opt/storm/apache-storm-${version} /opt/storm/latest
}


configure_storm_base () {
	juju-log "Configuring Storm general settings"
	# Setup basic configuration

	mkdir -p /mnt/storm
	sudo chown storm:storm /mnt/storm
	sed 's/storm.local.dir: \"storm-local\"/storm.local.dir: \"\/mnt\/storm\"/' < /opt/storm/apache-storm-${version}/conf/storm.yaml.tpl > /opt/storm/apache-storm-${version}/conf/storm.yaml
	chown storm:storm /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp -u $CHARM_DIR/storm.sh /etc/init.d/storm
	sed -i "s/%%%VERSION%%%/$version/g" /etc/init.d/storm
	chmod 755 /etc/init.d/storm
	update-rc.d storm defaults 91 1
}

open_ports () {
	juju-log "Configuring ports for service unit roles"
	case $role in
		master)
			#open-port `config-get nimbusport` # Nimbus Server
			open-port `config-get uiport` # Only user accessible ports should be opened.
			;;
		worker)
			#open-port `config-get drpcport` # DRPC
			;;
	esac
}

update_config () {
	juju-log "Updating Storm Configuration"
	nimbusmem=`config-get nimbusmemory`
	juju-log "nimbus:$nimbusmem"
	uimem=`config-get uimemory`
	juju-log "ui:$uimem"
	supervisormem=`config-get supervisormemory`
	juju-log "supervisor:$supervisormem"
	workermem=`config-get workermemory`
	juju-log "worker:$workermem"
	zkport=`config-get zookeeperport`
	juju-log "zk port:$zkport"
	nimbusport=`config-get nimbusport`
	juju-log "nimbus port:$nimbusport"
	uiport=`config-get uiport`
	juju-log "ui port:$uiport"
	drpcport=`config-get drpcport`
	juju-log "drpc port:$drpcport"
	nbrworkers=`config-get numberofworkers`
	juju-log "Number of workers:$nbrworkers"
	workerport=`config-get startingworkerport`
	juju-log "worker port start:$workerport"
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.childopts: .*/nimbus.childopts: \"-Xmx${nimbusmem}m\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/ui.childopts: .*/ui.childopts: \"-Xmx${uimem}m\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/supervisor.childopts: .*/supervisor.childopts: \"-Xmx${supervisormem}m\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/worker.childopts: .*/worker.childopts: \"-Xmx${workermem}m\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/storm.zookeeper.port: .*/storm.zookeeper.port: $zkport/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.thrift.port: .*/nimbus.thrift.port: $nimbusport/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/ui.port: .*/ui.port: $uiport/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/drpc.port: .*/drpc.port: $drpcport/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	workerports="["
	lastport=$(($workerport + $nbrworkers - 1))
	for n in `eval echo {$workerport..$lastport}`; do
		workerports="$workerports$n"
		if [ "$n" != "$lastport" ]; then
		   workerports="$workerports,"
		fi
	done
	workerports="$workerports]"
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/supervisor.slots.ports: .*/supervisor.slots.ports: $workerports/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
}

configure_master () {
	juju-log "Configuring nimbus for storm"
	nimbus=`unit-get private-address`
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.host: .*/nimbus.host: \"$nimbus\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	juju-log "Reconfiguring Storm DRPC configuration"
	for member in `relation-list`
	do
		address=`relation-get private-address $member`
		[ -z "$drpcs" ] && drpcs=\"$address\" || drpcs="$drpcs,\"$address\""
		port=`relation-get port $member`
	juju-log "$member - $address - $drpcs"
	done
	drpcs="$drpcs,\"$private_address\""
	# DRPC configuration reside in storm config
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/drpc.servers: .*/drpc.servers: [$drpcs]/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp

	relation-set master_node=$nimbus
	touch /opt/storm/apache-storm-${version}/conf/master
}

validate_master () {
	juju-log "Check if master configuration is still set-up"
	if [ ! -f /opt/storm/apache-storm-${version}/conf/master ]; then
		   configure_master
	fi
}

purge_master () {
	juju-log "Purging nimbus from storm"
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.host: .*/nimbus.host: /" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	rm -f /opt/storm/apache-storm-${version}/conf/master
}

configure_worker () {
	juju-log "Configuring supervisor for storm"
	MASTER=`relation-get master_node`
	juju-log "master: $MASTER"
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.host: .*/nimbus.host: \"$MASTER\"/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	touch /opt/storm/apache-storm-${version}/conf/worker
}

validate_worker () {
	juju-log "Check if worker configuration is still set-up"
	if [ ! -f /opt/storm/apache-storm-${version}/conf/worker ]; then
		   configure_worker
	fi
}

purge_worker () {
	juju-log "Purging supervisor configuration from storm"
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/nimbus.host: .*/nimbus.host: /" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	rm -f /opt/storm/apache-storm-${version}/conf/worker
}

update_coworkers () {
	juju-log "Reconfiguring Storm DRPC configuration"
	for member in `relation-list`
	do
		address=`relation-get private-address $member`
		[ -z "$drpcs" ] && drpcs=\"$address\" || drpcs="$drpcs,\"$address\""
		port=`relation-get port $member`
	juju-log "$member - $address - $drpcs"
	done
	drpcs="$drpcs,\"$private_address\""
	# DRPC configuration reside in storm config
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/drpc.servers: .*/drpc.servers: [$drpcs]/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
}

configure_zookeeper () {
	juju-log "Reconfiguring Storm zookeeper configuration"
	for member in `relation-list`
	do
		address=`relation-get private-address $member`
		[ -z "$zks" ] && zks=\"$address\" || zks="$zks,\"$address\""
		port=`relation-get port $member`
	juju-log "$member - $address - $zks"
	done
	# Zookeeper configuration reside in storm config
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/storm.zookeeper.servers: .*/storm.zookeeper.servers: [$zks]/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
}

purge_zookeeper () {
	juju-log "Purging zookeeper configuration from Storm"
	cp /opt/storm/apache-storm-${version}/conf/storm.yaml /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
	cat /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp | sed "s/storm.zookeeper.servers: .*/storm.zookeeper.servers: []/" > /opt/storm/apache-storm-${version}/conf/storm.yaml
	rm /opt/storm/apache-storm-${version}/conf/storm.yaml.tmp
}

# This function validates that both zookeeper and
# the dfs root have been configured which should
# be enough to start hbase
service_ready () {
	zk_configured && master_configured && return 0 || return 1
}

zk_configured () {
	# Validate that localhost has been substituted
	pattern="storm.zookeeper.servers: [\"localhost\"]"
	[ `grep -c "$pattern" /opt/storm/apache-storm-${version}/conf/storm.yaml` -eq 0 ] && return 0 || return 1
}

master_configured () {
	# Validate nimbus has been changed from localhost
	pattern="nimbus.host: \"localhost\""
	[ `grep -c "$pattern" /opt/storm/apache-storm-${version}/conf/storm.yaml` -eq 0 ] && return 0 || return 1
}

# Storm Service Control Commands
restart_storm () {
	juju-log "Restarting storm"
	stop_storm
	sleep 10
	start_storm
}

# This function is intelligent as it will
# only try to start start if its configured
# with appropriate relations
start_storm () {
	if service_ready
	then
		juju-log "Starting storm"
		service storm start || :
	fi
}

stop_storm () {
		juju-log "Stopping storm"
		service storm stop || :
}

resolve_role () {
	role="unconfigured"
	[ -d /opt/storm/apache-storm-${version}/conf/worker ] && role="worker" || :
	[ -d /opt/storm/apache-storm-${version}/conf/master ] && role="master" || :
	echo $role
}

give_hostname () {
	relation-set hostname=`hostname`
}

add_line_to_file () {
	# Add line to file if not already present
	LINE=$1
	FILE=$2
	grep -q "$LINE" "$FILE" || echo "$LINE" >> "$FILE"
}

add_hostname () {
	HOSTNAME=`relation-get hostname`
	if [ $? -eq 0 ]; then
		IP=`relation-get private-address`
		add_line_to_file "$IP $HOSTNAME\n" "/etc/hosts"
	fi
}



COMMAND=`basename $0`
role="`resolve_role`"

case $COMMAND in
	install)
		configure_hosts
		install_base_packages
		configure_storm_base
		;;
	worker-relation-joined)
		give_hostname
		;;
	master-relation-changed)
	  add_hostname
		ready=`relation-get ready`
		if [ -z "$ready" ]
		then
			juju-log "Master not ready - waiting"
			exit 0
		else
			juju-log "Master ready - starting master"
			start_storm
		fi
		;;
	master-relation-departed|master-relation-broken)
		juju-log "No master relation - dropping config and terminating master"
		purge_master
		stop_storm
		;;
	zookeeper-relation-changed|zookeeper-relation-departed)
		configure_zookeeper
		start_storm
		;;
	zookeeper-relation-broken)
		juju-log "No Zookeeper - dropping config and terminating storm"
		purge_zookeeper
		stop_storm
		;;
	master-relation-joined)
	  give_hostname
		case $role in
			unconfigured)
				juju-log "Configuring this unit as a master"
				role="master"
				configure_master
				open_ports
				start_storm
				sleep 30  # TODO this should probably live in packaging
				relation-set ready="true"
				;;
			master)
				juju-log "Already configured as master"
				# Unit should only ever assume this role once
				# but it might be stopped due to a break between
				# itself and zookeeper - so try to start
				validate_master
				start_storm
				relation-set ready="true"
				;;
			worker)
				juju-log "Already configured as another role: $role"
				exit 1
				;;
		esac
		;;
	worker-relation-changed)
  	add_hostname
		ready=`relation-get ready`
		if [ -z "$ready" ]
		then
			juju-log "Master not ready - waiting"
			exit 0
		else
			juju-log "Master ready"
			case $role in
				unconfigured)
					juju-log "Configuring this unit as a worker"
					role="worker"
					configure_worker
					open_ports
					start_storm
					;;
				worker)
					juju-log "Already configured as worker"
					# Unit should only ever assume this role once
					# but it might be stopped due to a break between
					# itself and a master - so try to start
					validate_worker
					start_storm
					;;
				master)
					juju-log "Already configured as another role: $role"
					exit 1
					;;
			esac
		fi
		;;
	coworker-relation-joined|coworker-relation-broken|worker-relation-departed)
	  give_hostname
		update_coworkers
		restart_storm
		;;
	coworker-relation-changed)
	  add_hostname
	  # Don't do anything
		;;
	worker-relation-broken|worker-relation-departed)
		# No master - always shutdown
  	#purge_worker
		#stop_storm
		;;
	config-changed)
		update_config
	restart_storm
		;;
	upgrade-charm)
		juju-log "not implemented"
		;;
	*)
		juju-log "Command not recognised: $COMMAND"
		;;
esac
