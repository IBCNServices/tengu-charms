#!/bin/bash
# This script does all the stuf that is needed to make a Virtual Wall node ready for Tengu.
# Please be aware that all changes to this script need to be backwards compatible, since all instances automatically download the latest version.

SCRIPTPATH=`readlink -f $0`
ipaddr=$(ifconfig |grep -B1 "inet addr" |awk '{ if ( $1 == "inet" ) { print $2 } else if ( $2 == "Link" ) { printf "%s:" ,$1 } }' |awk -F: '{ print $1 ": " $3 }')
hostname=$(hostname --fqdn)

if [[ $1 == "resize" ]] ; then
  resize2fs /dev/$2
  sed -i "\@^$SCRIPTPATH resize $2 >> /var/log/afterextend.log\$@d" /etc/rc.local
  exit
fi

sudo apt-get update; sudo locale-gen nl_BE.UTF-8; sudo useradd safety --uid 30000

# NAT config
if [[ $ipaddr == *"193.190."* ]]; then
  echo "Node has public IP. Skipping NAT config"
else
  if [[ $hostname == *".wall1.ilabt.iminds.be" ]]; then
    if [[ $hostname == *"-vm"* ]]; then
      echo "hostname: $hostname; Configuring NAT and routes for VM on wall1";
      echo 'Wall1 NAT is currently not working; will not change routes.';
      # sudo route add -net 10.2.0.0 netmask 255.255.240.0 gw 172.16.0.1
      # sudo route del default gw 172.16.0.1 && sudo route add default gw 172.16.0.2
      # sudo route add -net 157.193.135.0 netmask 255.255.255.0 gw 172.16.0.1
      # sudo route add -net 157.193.214.0 netmask 255.255.255.0 gw 172.16.0.1
      # sudo route add -net 157.193.215.0 netmask 255.255.255.0 gw 172.16.0.1
      # sudo route add -net 192.168.126.0 netmask 255.255.255.0 gw 172.16.0.1
      # sudo route add -net 10.2.32.0 netmask 255.255.240.0 gw 172.16.0.1
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
  elif [[ $hostname == *".wall2.ilabt.iminds.be" ]]; then
    if [[ $hostname == *"-vm"* ]]; then
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
    echo "ERROR: hostname: $hostname is not part of wall1 or wall2, will not configure NAT";
    exit 1
  fi
fi

# root expansion
if [[ $hostname == *"-vm"* ]]; then
  echo "hostname: $hostname; Node is a VM, will not expand root partition"
else
  echo "Will resize root partition"
  ROOTDEV=$(lsblk --raw | grep / | tr -s ' ' | cut -d ' ' -f 1)
  SWAPDEV=$(lsblk --raw | grep 'SWAP' | tr -s ' ' | cut -d ' ' -f 1)
  FREE_SIZE=$(lsblk --raw | grep 'sda4' |  tr -s ' ' | cut -d ' ' -f 4 | cut -d '.' -f 1 | cut -d ',' -f 1)
  START_ROOT=$(cat /sys/class/block/$ROOTDEV/start)
  #We have two known cases:
  if [[ $ROOTDEV == "sda2" && $SWAPDEV == 'sda3' ]]; then
    echo 'assuming this is an MBRv2 image since root device $ROOTDEV = sda2 (Ubuntu 12.04 images)'
    fdisk /dev/sda << EOF
    d
    2
    d
    3
    d
    4
    n
    p
    2
    $START_ROOT
    +${FREE_SIZE}GB
    n
    p
    3

    +12GB
    t
    2
    83
    t
    3
    82
    a
    2
    w
EOF
    echo "$SCRIPTPATH resize $ROOTDEV >> /var/log/afterextend.log" | tee -a /etc/rc.local
    sleep 10
    reboot
  elif [[ ( $ROOTDEV == "sda1" ) && ( $START_ROOT == '2048' ) && ( $SWAPDEV == 'sda3' ) && "$FREE_SIZE" ]]; then
    echo 'assuming this is an MBRv3 image since root device $ROOTDEV = sda1 (Ubuntu 14.04 images)'
    fdisk /dev/sda << EOF
    d
    1
    d
    2
    d
    3
    d
    n
    p
    1
    $START_ROOT
    +${FREE_SIZE}GB
    n
    p
    3

    +12GB
    t
    1
    83
    t
    3
    82
    a
    1
    w
EOF
    echo "$SCRIPTPATH resize $ROOTDEV >> /var/log/afterextend.log" | tee -a /etc/rc.local
    sleep 10
    reboot
  else
    echo "I don't recognize this partion layout. rootdev=$ROOTDEV, start_root=$START_ROOT, swapdev=$SWAPDEV, freesize=$FREE_SIZE"
  fi
fi
