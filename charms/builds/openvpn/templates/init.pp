# Copyright (C) 2017  Ghent University
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
include openvpn
# add a server instance
openvpn::server { '{{servername}}':
  country      => '{{country}}',
  province     => '{{province}}',
  city         => '{{city}}',
  organization => '{{organization}}',
  email        => '{{email}}',
  server       => '10.200.200.0 255.255.255.0',
  # udp = faster but many firewalls block it
  proto        => '{{protocol}}',
  port         => '{{port}}',
  # Accept connections on the external ip. We cannot leave this empty because
  # then we have the chance that the vpn server will respond using a different
  # interface than where he got the request from. The client does not like this.
  # Another solution is to use multihome: https://community.openvpn.net/openvpn/ticket/442
  # However, multihome is not supported in the puppet library we're using; it
  # has a slight performance drop, and we only put 1 IP in the client config
  # file so "binding to all interfaces" is useless since the clients only know
  # one interface.
  local        => '{{ext_ip}}',

  # DH key size.
  # - 2048 = recommended;
  # - 4096 = upper limit (clients might not support higher)
  # More info: https://community.openvpn.net/openvpn/wiki/Hardening
  ssl_key_size => '2048',
  # Authenticate the TLS channel with a PSK that is shared among all peers.
  #  This is mostly to protect from DOS attacks. Traffic on the TLS channel
  #  has a high crypto/cpu load. An attacker might send garbage traffic on this
  #  channel to overload the cpu of the server. The PSK enables the server to
  #  drop garbage traffic before doing crypto, this makes it hard to overload
  #  the cpu by sending garbage traffic on the TLS channel. Note that this only
  #  works against attackers that don't have the PSK, won't protect you from
  #  an angry ex-employee.
  tls_auth     => true,

  # Will multiple clients connect with the same certificate/key
  # files or common names?
{% if duplicate_cn %}  duplicate_cn => true, {% endif %}
  # We want to push to the clients
  # - our DNS server
  # - routes to the networks we know
  #

  push         => [
  {%- if push_dns %}
    "dhcp-option DNS {{dns_server}}",
    {% for dns_search_domain in dns_search_domains -%}
    "dhcp-option DOMAIN {{dns_search_domain}}",
    {%- endfor %}
    {% for network in internal_networks -%}
    "route {{network}}",
    {%- endfor %}
  {%- endif %}
  {%- if push_default_gateway %}
  "redirect-gateway def1 bypass-dhcp"
  {%- endif %}
  ],
}

# define clients
{% for client in clients %}
openvpn::client { '{{client}}':
 server         => '{{servername}}',
 remote_host    => '{{pub_ip}}',
 port           => '{{port}}',
 proto          => '{{protocol}}',
 tls_auth       => 'true',
 # We have to specify key-direction manually due to the following bug:
 # https://github.com/luxflux/puppet-openvpn/issues/224
 custom_options => {
   "key-direction" => "1",
 },
}
{% endfor %}

# Enable forwarding of traffic so we can become a (NAT) router for
# the clients connecting to the VPN
sysctl { "net.ipv4.ip_forward":
  ensure => present,
  value  => "1",
}

# Set firewall rules
include firewall

# firewall { '120 allow {{port}}/TCP for OpenVPN':
#   state  => 'NEW',
#   dport  => '{{port}}',
#   proto  => '{{protocol}}',
#   action => 'accept',
# }
#
# firewall { '121 allow TUN connections':
#   chain   => 'INPUT',
#   proto   => 'all',
#   iniface => 'tun+',
#   action  => 'accept',
# }
#
# firewall { '122 forward TUN forward connections':
#   chain   => 'FORWARD',
#   proto   => 'all',
#   iniface => 'tun+',
#   action  => 'accept',
# }
#
# firewall { '123 tun+ to *':
#   chain    => 'FORWARD',
#   proto    => 'all',
#   iniface  => 'tun+',
#   state    => [ 'ESTABLISHED', 'RELATED' ],
#   action   => 'accept',
# }
#
# firewall { '124 * to tun+':
#   chain    => 'FORWARD',
#   proto    => 'all',
#   outiface => 'tun+',
#   state    => [ 'ESTABLISHED', 'RELATED' ],
#   action   => 'accept',
# }

# NAT translation

firewall { '125 POSTROUTING':
  table    => 'nat',
  proto    => 'all',
  chain    => 'POSTROUTING',
  source   => "10.200.200.0/24",
  jump     => 'MASQUERADE',
}
