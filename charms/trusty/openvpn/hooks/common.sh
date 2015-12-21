#!/bin/bash
set -e

# Set static variables
SERVER_CONF=/etc/openvpn/server.conf
DEFAULT_CLIENT_CONF=/etc/openvpn/client.ovpn
PROTO=`config-get protocol`
PORT=`config-get port`
DEFAULT_GW_IP=`ip route get 8.8.8.8 | grep src | tr -s ' ' | rev | cut -d ' ' -f 2 | rev`
PUBLIC_IP=`unit-get public-address`
NETWORK=10.8.0.0/8

# Convert a CIDR notation to netmask for use with the route command.
# Essentially, this will take a CIDR value (/1-32) and return a
# subnet mask (e.x. 255.255.255.0).
# Adapted from:
#   https://www.linuxquestions.org/questions/programming-9/bash-cidr-calculator-646701/#post3433298
function convert_cidr {
  local i netmask=""
  local cidr=$1
  local abs=$(($cidr/8))
  for ((i=0;i<4;i+=1)); do
    if [ $i -lt $abs ]; then
      netmask+="255"
    elif [ $i -eq $abs ]; then
      netmask+=$((256 - 2**(8-$(($cidr%8)))))
    else
      netmask+=0
    fi
    test $i -lt 3 && netmask+="."
  done
  echo $netmask
}

# Parses a network given in the "x.x.x.x/xx" notation and returns a
# "x.x.x.x x.x.x.x" network and subnet mask notation.
function parse_network {
  local full_net=$1
  local network=`echo ${full_net} | cut -d'/' -f1`
  local cidr=`echo ${full_net} | cut -d'/' -f2`
  cidr=`convert_cidr ${cidr}`
  echo "${network} ${cidr}"
}

create_user () {
  USER=$1
  # Check to see if a user certificate has been generated. If one
  # has not, then go ahead and create one. Next, create a directory
  # for the user and copy the user and server certs/keys as well as
  # the client config. Create a nice little tarball and place it in
  # the ubuntu user's home directory for download via SCP and remove
  # the temp directory.
  juju-log "Creating user certificate"
  EASYRSA_DIR=/etc/openvpn/easy-rsa
  CLIENT_DIR=/etc/openvpn/easy-rsa/${USER}_keys
  CLIENT_CONFIG=$CLIENT_DIR/client.ovpn
  cd $EASYRSA_DIR

  if [ ! -d "$CLIENT_DIR" ]; then
    juju-log "Generating new certificate for user ${USER}"
    source $EASYRSA_DIR/vars
    $EASYRSA_DIR/pkitool $USER
    mkdir -p $CLIENT_DIR
    cp  $DEFAULT_CLIENT_CONF\
        $EASYRSA_DIR/keys/ca.crt\
        $EASYRSA_DIR/keys/$USER.crt\
        $EASYRSA_DIR/keys/$USER.key\
        $CLIENT_DIR
    sed -r -i -e "s/cert .*\.crt/cert ${USER}.crt/g" $CLIENT_CONFIG
    sed -r -i -e "s/key .*\.key/key ${USER}.key/g" $CLIENT_CONFIG
  fi

  # Generate list of ips and hostnames to put in config file. Default gateway ip is first, then public ip the all the others. Remove tunnel ip.
  ips=($(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'))
  tunip=$(ip addr | awk '/inet/ && /tun0/{sub(/\/.*$/,"",$2); print $2}')
  ips=(${ips[@]/$tunip})
  ips=(${ips[@]/$PUBLIC_IP})
  ips=($PUBLIC_IP "${ips[@]}")
  ips=(${ips[@]/$DEFAULT_GW_IP})
  ips=($DEFAULT_GW_IP "${ips[@]}")
  # Remove all remotes of config file
  sed -r -i -e "/^remote.*/d" $CLIENT_CONFIG
  # Add new remotes to config file
  SEDCOMMAND="sed -i '/# to load balance between the servers./a \\"
  for IP in "${ips[@]}"; do
    SEDCOMMAND+="remote ${IP} ${PORT}\n"
  done
  SEDCOMMAND="${SEDCOMMAND}' $CLIENT_CONFIG"
  echo "DEBUG: $SEDCOMMAND"
  eval $SEDCOMMAND


  # to load balance between the servers.

  sed -r -i -e "s/proto (tcp|udp).*/proto ${PROTO}/g" $CLIENT_CONFIG
  tar -czf /home/ubuntu/$USER.tgz ${USER}_keys
  echo "User settings ready for download. Located at /home/ubuntu/$USER.tgz"
}
