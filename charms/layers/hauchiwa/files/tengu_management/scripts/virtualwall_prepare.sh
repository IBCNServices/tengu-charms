#!/bin/bash
# This script does all the stuf that is needed to make a Virtual Wall node ready for Tengu.
# Run this script as root. Emulab boot scripts run as geniuser so it is required to use `sudo` to run this.
# Please be aware that all changes to this script need to be backwards compatible, since all instances automatically download the latest version.
#set -e

# Log output of this script
exec >> /var/log/tengu-prepare.log
exec 2>&1

SCRIPTPATH=`readlink -f $0`

# resize and exit if requested
if [[ $1 == "resize" ]]; then
  resize2fs /dev/$2
  sed -i "\@^$SCRIPTPATH resize $2\$@d" /etc/rc.local
  touch '/var/log/tengu-init-done'
  exit
fi

# exit if we already expanded, so we don't get lost in an infinite reboot cycle
# in the case this script gets called after each reboot
if [[ -f /var/log/tengu-expansion-done ]]; then
  exit
fi

export https_proxy=http://proxy.atlantis.ugent.be:8080

# Fix for weird apt errors
apt-get update
# Fix for locale not found error when ssh-ing from belgian Linux machine
locale-gen nl_BE.UTF-8
# Emulab creates users with fixed userids starting from userid 20000.
# Emulab assumes no other users are added.
# Next line makes sure new users will not have userid that emulab uses.
useradd safety --uid 30000

# Get help script
wget https://raw.githubusercontent.com/galgalesh/tengu-charms/master/charms/layers/hauchiwa/files/tengu_management/scripts/get_pubipv4.py -O /get_pubipv4.py
chmod u+x /get_pubipv4.py

# Get required values
ORIG_PUB_IPADDR=$(hostname -i | cut -d ' ' -f 2) # only works if hostname is resolvable
PUB_IF=$(ifconfig | grep -B1 "inet addr:$ORIG_PUB_IPADDR" | awk '$1!="inet" && $1!="--" {print $1}')
HOSTNAME=$(hostname --fqdn)
NEW_PUBIPV4=$(/get_pubipv4.py)

# Init empty array of network configuration commands
NET_CONFIG=()

# Add public ipv4 commands if we got assigned one
if [[ "$NEW_PUBIPV4" ]]; then
  if [[ ( "$HOSTNAME" == *".wall1.ilabt.iminds.be" ) ]]; then
    PUB_GATEWAY='193.190.127.129'
  else
    PUB_GATEWAY='193.190.127.193'
  fi
  NET_CONFIG+=(
    "vconfig add ${PUB_IF} 29"
    "ifconfig ${PUB_IF}.29 $NEW_PUBIPV4"
    "route del default && route add default gw $PUB_GATEWAY"
  )
fi

IP_ADRESSES=$(ifconfig | awk -F "[: ]+" '/inet addr:/ { if ($4 != "127.0.0.1") print $4 }')

# Get Values for route commands
if [[ "$HOSTNAME" == *".wall1.ilabt.iminds.be" ]]; then
  OTHER_WALL='10.2.32.0'
  if [[ "$HOSTNAME" == *"-vm"* ]]; then
    IBCN_GATEWAY='172.16.0.1'
    PUB_GATEWAY='172.16.0.2'
    OTHER_TYPE_IP='10.2.0.0'
    OTHER_TYPE_NETMASK='255.255.240.0'
  else
    IBCN_GATEWAY='10.2.15.254'
    PUB_GATEWAY='10.2.15.253'
    OTHER_TYPE_IP='10.11.0.0'
    OTHER_TYPE_NETMASK='255.255.0.0'
  fi
elif [[ "$HOSTNAME" == *".wall2.ilabt.iminds.be" ]]; then
  OTHER_WALL='10.2.0.0'
  if [[ "$HOSTNAME" == *"-vm"* ]]; then
    IBCN_GATEWAY='172.16.0.1'
    PUB_GATEWAY='172.16.0.2'
    OTHER_TYPE_IP='10.2.32.0'
    OTHER_TYPE_NETMASK='255.255.240.0'
  else
    IBCN_GATEWAY='10.2.47.254'
    PUB_GATEWAY='10.2.47.253'
    OTHER_TYPE_IP='10.11.0.0'
    OTHER_TYPE_NETMASK='255.255.0.0'
  fi
fi


# if not directly connected to internet, add new NATted default gateway
if [[ ! ( $IP_ADRESSES == *'193'* ) ]]; then
  NET_CONFIG+=(
    "route del default gw $IBCN_GATEWAY && route add default gw $PUB_GATEWAY"
  )
fi

# If there is an interface connected to ibcn network, add routes for ibcn network
if [[ $IP_ADRESSES == *'10.2.'* || $IP_ADRESSES == *'172.16.'* ]]; then
  NET_CONFIG+=(
    "route add -net $OTHER_TYPE_IP netmask $OTHER_TYPE_NETMASK gw $IBCN_GATEWAY"
    "route add -net 157.193.135.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"
    "route add -net 157.193.214.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"
    "route add -net 157.193.215.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"
    "route add -net 192.168.126.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"
    "route add -net $OTHER_WALL netmask 255.255.240.0 gw $IBCN_GATEWAY"
  )
fi

# execute commands
for CONFIG_COMMAND in "${NET_CONFIG[@]}"; do
  echo "DEBUG: $CONFIG_COMMAND"
  eval $CONFIG_COMMAND
done

# Persist commands in /etc/network/interfaces
SEDCOMMAND="sed -i '/    up echo \"Emulab control net is \$IFACE\"/a \\"
for CONFIG_COMMAND in "${NET_CONFIG[@]}"; do
  SEDCOMMAND="${SEDCOMMAND}    up $CONFIG_COMMAND\n"
done
SEDCOMMAND="${SEDCOMMAND}' /etc/network/interfaces"
echo "DEBUG: $SEDCOMMAND"
eval $SEDCOMMAND



# root expansion
if [[ "$HOSTNAME" == *"-vm"* ]]; then
  echo "hostname: "$HOSTNAME"; Node is a VM, will not expand root partition"
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
    echo "$SCRIPTPATH resize $ROOTDEV" | tee -a /etc/rc.local
    touch /var/log/tengu-expansion-done
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
    echo "$SCRIPTPATH resize $ROOTDEV" | tee -a /etc/rc.local
    touch /var/log/tengu-expansion-done
    sleep 10
    reboot
  else
    echo "I don't recognize this partion layout. rootdev=$ROOTDEV, start_root=$START_ROOT, swapdev=$SWAPDEV, freesize=$FREE_SIZE"
  fi
fi

touch /var/log/tengu-expansion-done
