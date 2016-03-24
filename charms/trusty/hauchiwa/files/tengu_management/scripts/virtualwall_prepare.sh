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
IP_ADRESSES=$(ifconfig | awk -F "[: ]+" '/inet addr:/ { if ($4 != "127.0.0.1") print $4 }')

# Init empty array of network configuration commands
NET_CONFIG=()

# Add public ipv4 commands if we got assigned one
if [[ "$NEW_PUBIPV4" ]]; then
  if [[ ( "$HOSTNAME" == *".wall1.ilabt.iminds.be" ) ]]; then
    PUB_GATEWAY='193.190.127.129'
    V_IF='28'
  else
    PUB_GATEWAY='193.190.127.193'
    V_IF='29'
  fi
  NET_CONFIG+=(
    "vconfig add ${PUB_IF} ${V_IF}"
    "ifconfig ${PUB_IF}.${V_IF} $NEW_PUBIPV4"
    "route del default && route add default gw $PUB_GATEWAY"
  )
fi


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
if [[ ! ( $IP_ADRESSES == *'193'* ) && ! $NEW_PUBIPV4 ]]; then
  NET_CONFIG+=(
    "route del default gw $IBCN_GATEWAY && route add default gw $PUB_GATEWAY"
  )
fi

# If there is an interface connected to ibcn network, add routes for ibcn network
if [[ $IP_ADRESSES == *'10.2.'* || $IP_ADRESSES == *'172.16.'* ]]; then
  NET_CONFIG+=(
    "route add -net $OTHER_TYPE_IP netmask $OTHER_TYPE_NETMASK gw $IBCN_GATEWAY"
    "route add -net 157.193.135.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"
#    "route add -net 157.193.214.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"  # Apparently, these break connections to intec servers
#    "route add -net 157.193.215.0 netmask 255.255.255.0 gw $IBCN_GATEWAY"  # Apparently, these break connections to intec servers
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

# Persist control interface
# /usr/local/etc/emulab/findcnet tries to guess what the control interface is by doing a dhcp-discover. The first interface that receives a dhcp response is the control interface. This fails when the private network also has a dhcp server (as is the case in an installed Tengu).
# During first boot, the private dhcp-server is not yet installed. so geni-get will find the correct interface. We persist this interface in the findcnet script. We use the mac address and get the interface from the mac address because interface names may change after reboot.
CONTROL_MAC=$(geni-get control_mac | sed -e 's/\([0-9A-Fa-f]\{2\}\)/\1:/g' -e 's/\(.*\):$/\1/')
sed -i "/# Find a list of candidate interface/i \
\ \ \ \ _iflist=\$(ifconfig -a | grep $CONTROL_MAC | cut -f1 -d ' ')" /usr/local/etc/emulab/findcnet
sed -ri '/# Find a list of candidate interfaces/,+3d' /usr/local/etc/emulab/findcnet


# root expansion
if [[ "$HOSTNAME" == *"-vm"* ]]; then
  echo "hostname: "$HOSTNAME"; Node is a VM, will not expand root partition"
else
  echo "Will reformat disk sda"
  DEV='sda'
  ROOT_DEV=$(lsblk --raw | grep / | tr -s ' ' | cut -d ' ' -f 1)
  ROOT_PART_NUM=$(echo $ROOT_DEV | sed "s/sda//")
  ROOT_STARTBLOCK=$(cat /sys/class/block/$ROOT_DEV/start)

  SWAP_DEV=$(lsblk --raw | grep 'SWAP' | tr -s ' ' | cut -d ' ' -f 1)
  SWAP_PART_NUM=$(echo $SWAP_DEV | sed "s/sda//")

  #SECTORS=$(fdisk /dev/sda -l | grep sectors | head -n 1 | rev |  cut -d ' ' -f 2 | rev)
  SECTOR_SIZE=$(fdisk /dev/sda -l | grep "Sector size (logical/physical)" | cut -d ' ' -f 4)
  #LAST_SECTOR=$(fdisk /dev/sda -l | grep /dev/ |  tail -n 1 | tr -s ' ' | cut -d ' ' -f 3)
  TEMP=$(( $ROOT_STARTBLOCK * $SECTOR_SIZE ))
  UNALL_SIZE_BEFORE_ROOT=$( bc <<< "a=$TEMP; b=1073741824; if ( a%b ) a/b+1 else a/b" )
  echo "Sector size is $SECTOR_SIZE, start of root is $ROOT_STARTBLOCK, ceil(Unallocated size before root) is ${UNALL_SIZE_BEFORE_ROOT}GB"
  DISK_SIZE=$( fdisk -l /dev/sda | grep 'Disk /dev/sda:' | cut -d ' ' -f 3 | cut -d '.' -f 1 | cut -d ',' -f 1 )
  USABLE_SIZE=$(( $DISK_SIZE - $UNALL_SIZE_BEFORE_ROOT ))
  echo "Disk size is ${DISK_SIZE}GB. Total usable size is ${USABLE_SIZE}GB"

  RAM_SIZE=$(( $(free -m | grep Mem: | tr -s ' ' | cut -d ' ' -f 2) / 1024 ))  # RAM size in GB

  PARTITIONS=( $(eval echo {$ROOT_PART_NUM..4}) )  # Only partitions >= root part num can be used
  DEFAULT=0
  ALL_SIZE=0
  DEL_PART_COMMAND=''
  for PART_NUM in "${PARTITIONS[@]}"; do
    DEL_PART_COMMAND+=$'\nd\n'$PART_NUM
  done

  SWAP_NEW_SIZE="$(( $RAM_SIZE * 2 ))"            # Swap size is RAM * 2 (in GB)
  ROOT_NEW_SIZE=$(( $USABLE_SIZE - $SWAP_NEW_SIZE - 10 )) # -10 because fdisk allocates more than asked. This isn't an exact science.
  # Swap size will not be explicitly specified. Swap takes up all the remaining space on the disk. This will be more than SWAP_NEW_SIZE on small disks and less than SWAP_NEW_SIZE on large disks.

  echo "DEV=$DEV ROOTDEV=$ROOT_DEV ROOT_STARTBLOCK=$ROOT_STARTBLOCK SWAP_DEV=$SWAP_DEV"
  echo "Resizing root to ${ROOT_NEW_SIZE}GB and swap to ${SWAP_NEW_SIZE}GB"

  fdisk /dev/sda << EOF
  $DEL_PART_COMMAND
  n
  p
  $ROOT_PART_NUM
  $ROOT_STARTBLOCK
  +${ROOT_NEW_SIZE}G
  n
  p
  $SWAP_PART_NUM


  t
  $ROOT_PART_NUM
  83
  t
  $SWAP_PART_NUM
  82
  a
  $ROOT_PART_NUM
  w
EOF
  echo "$SCRIPTPATH resize $ROOT_DEV" | tee -a /etc/rc.local
  touch /var/log/tengu-expansion-done
  sleep 10
  reboot
fi

touch /var/log/tengu-expansion-done
