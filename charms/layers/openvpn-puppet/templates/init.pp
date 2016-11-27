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
  # Accept connections on all interfaces
  local        => '',
  #DH key size. 1024 = default; 2048 = paranoid
  ssl_key_size => '2048',
  # Will multiple clients connect with the same certificate/key
  # files or common names?
{% if duplicate_cn %}  duplicate_cn => true, {% endif %}
  # We want to push to the clients
  # - our DNS server
  # - routes to the networks we know
  #

  push         => [
{% if push_dns %}
    "dhcp-option DNS {{dns_server}}",
    "dhcp-option DOMAIN {{dns_search_domain}}",
{% endif %}
  ],
}

# define clients
{% for client in clients %}
openvpn::client { '{{client}}':
 server => '{{servername}}',
 remote_host => '{{ext_ip}}',
}
{% endfor %}
# Enable forwarding of traffic so we can become a (NAT) router for
# the clients connecting to the VPN

file { '/etc/sysctl.conf':
  ensure => file,
}

exec { 'sysctl -p':
  command     => '/sbin/sysctl -p',
  refreshonly => true,
  subscribe   => File['/etc/sysctl.conf'],
}

augeas { 'sysctl_ip_forward':
  context => '/files/etc/sysctl.conf',
  onlyif  => "get net.ipv4.ip_forward == '0'",
  changes => "set net.ipv4.ip_forward '1'",
  notify  => Exec['sysctl -p'],
}



# Set firewall rules
include firewall

firewall { '120 allow {{port}}/TCP for OpenVPN':
  state  => 'NEW',
  dport  => '{{port}}',
  proto  => '{{protocol}}',
  action => 'accept',
}

firewall { '121 allow TUN connections':
  chain   => 'INPUT',
  proto   => 'all',
  iniface => 'tun+',
  action  => 'accept',
}

firewall { '122 forward TUN forward connections':
  chain   => 'FORWARD',
  proto   => 'all',
  iniface => 'tun+',
  action  => 'accept',
}

firewall { '123 tun+ to *':
  chain    => 'FORWARD',
  proto    => 'all',
  iniface  => 'tun+',
  state    => [ 'ESTABLISHED', 'RELATED' ],
  action   => 'accept',
}

firewall { '124 * to tun+':
  chain    => 'FORWARD',
  proto    => 'all',
  outiface => 'tun+',
  state    => [ 'ESTABLISHED', 'RELATED' ],
  action   => 'accept',
}

# NAT translation

firewall { '125 POSTROUTING':
  table    => 'nat',
  proto    => 'all',
  chain    => 'POSTROUTING',
  source   => "10.200.200.0/24",
  jump     => 'MASQUERADE',
}
