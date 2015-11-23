#!/bin/bash
# This script configures the NAT routes for a node on the virtual wall 1 and 2.
# VM's are not yet configured exactly as they should.
ipaddr=$(ifconfig |grep -B1 "inet addr" |awk '{ if ( $1 == "inet" ) { print $2 } else if ( $2 == "Link" ) { printf "%s:" ,$1 } }' |awk -F: '{ print $1 ": " $3 }')
if [[ $ipaddr == *"193.190."* ]]
then
  echo "Node has public IP. Skipping NAT config"
  exit 0
fi

hostname=$(hostname --fqdn)
if [[ $hostname == *".wall1.ilabt.iminds.be" ]]
then
  if [[ $hostname == *"-vm"* ]]
  then
    echo "hostname: $hostname; Configuring NAT and routes for VM on wall1";
    sudo route add -net 10.2.0.0 netmask 255.255.240.0 gw 172.16.0.1
    sudo route del default gw 172.16.0.1 && sudo route add default gw 172.16.0.2
    sudo route add -net 157.193.135.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 157.193.214.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 157.193.215.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 192.168.126.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 10.2.32.0 netmask 255.255.240.0 gw 172.16.0.1
  else
    echo "hostname: $hostname; Configuring NAT and routes for physical node on wall1";
    sudo route del default gw 10.2.15.254 && sudo route add default gw 10.2.15.253
    sudo route add -net 10.11.0.0 netmask 255.255.0.0 gw 10.2.15.254
    sudo route add -net 157.193.135.0 netmask 255.255.255.0 gw 10.2.15.254
    sudo route add -net 157.193.214.0 netmask 255.255.255.0 gw 10.2.15.254
    sudo route add -net 157.193.215.0 netmask 255.255.255.0 gw 10.2.15.254
    sudo route add -net 192.168.126.0 netmask 255.255.255.0 gw 10.2.15.254
    sudo route add -net 10.2.32.0 netmask 255.255.240.0 gw 10.2.15.254
  fi
elif [[ $hostname == *".wall2.ilabt.iminds.be" ]]
then
  if [[ $hostname == *"-vm"* ]]
  then
    echo "hostname: $hostname; Configuring NAT and routes for VM on wall2";
    sudo route add -net 10.2.32.0 netmask 255.255.240.0 gw 172.16.0.1
    sudo route del default gw 172.16.0.1 && sudo route add default gw 172.16.0.2
    sudo route add -net 157.193.135.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 157.193.214.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 157.193.215.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 192.168.126.0 netmask 255.255.255.0 gw 172.16.0.1
    sudo route add -net 10.2.0.0 netmask 255.255.240.0 gw 172.16.0.1
  else
    echo "hostname: $hostname; Configuring NAT and routes for physical node on wall2";
    sudo route del default gw 10.2.47.254 && sudo route add default gw 10.2.47.253
    sudo route add -net 10.11.0.0 netmask 255.255.0.0 gw 10.2.47.254
    sudo route add -net 157.193.135.0 netmask 255.255.255.0 gw 10.2.47.254
    sudo route add -net 157.193.214.0 netmask 255.255.255.0 gw 10.2.47.254
    sudo route add -net 157.193.215.0 netmask 255.255.255.0 gw 10.2.47.254
    sudo route add -net 192.168.126.0 netmask 255.255.255.0 gw 10.2.47.254
    sudo route add -net 10.2.0.0 netmask 255.255.240.0 gw 10.2.47.254
  fi
else
  echo "ERROR: hostname: $hostname is not part of wall1 or wall2";
  exit 1
fi
