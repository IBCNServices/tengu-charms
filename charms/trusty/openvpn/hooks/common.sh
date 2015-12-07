#!/bin/bash

# Set static variables
SERVER_CONF=/etc/openvpn/server.conf
DEFAULT_CLIENT_CONF=/etc/openvpn/client.ovpn
PROTO=`config-get protocol`
PORT=`config-get port`
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
  if ! `ls /etc/openvpn/easy-rsa/keys/ | grep -q ${USER}`; then
    juju-log "Generating new certificate for user ${USER}"
    # Update the client config settings to include public IP and user certificates
    sed -r -i -e "s/^remote.*/remote ${PUBLIC_IP} ${PORT}/g" $DEFAULT_CLIENT_CONF
    sed -r -i -e "s/cert .*\.crt/cert ${USER}.crt/g" $DEFAULT_CLIENT_CONF
    sed -r -i -e "s/key .*\.key/key ${USER}.key/g" $DEFAULT_CLIENT_CONF
    sed -r -i -e "s/proto (tcp|udp).*/proto ${PROTO}/g" $DEFAULT_CLIENT_CONF
    cd /etc/openvpn/easy-rsa && source ./vars
    /etc/openvpn/easy-rsa/pkitool $USER
    mkdir ${USER}_keys
    cp $DEFAULT_CLIENT_CONF keys/ca.crt keys/$USER.crt keys/$USER.key ${USER}_keys/
    tar -czf /home/ubuntu/$USER.tgz ${USER}_keys
    rm -Rf ${USER}_keys
    print "User settings ready for download. Located at /home/ubuntu/$USER.tgz"
  else
    juju-log "Updating config for user ${USER}"
    CLIENT_CONFIG=${USER}_keys/client.ovpn
    cd /etc/openvpn/easy-rsa
    sed -r -i -e "s/^remote.*/remote ${PUBLIC_IP} ${PORT}/g" $CLIENT_CONFIG
    sed -r -i -e "s/proto (tcp|udp).*/proto ${PROTO}/g" $CLIENT_CONFIG
  fi
}
