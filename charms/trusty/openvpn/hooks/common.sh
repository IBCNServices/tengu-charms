#!/bin/bash

# Set static variables
HOME=`dirname $0`
EASY_RSA=/etc/openvpn/easy-rsa
PKITOOL=$EASY_RSA/pkitool
SERVER_CONF=/etc/openvpn/server.conf
CLIENT_CONF=/etc/openvpn/client.ovpn

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
