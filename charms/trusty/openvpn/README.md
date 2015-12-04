# Overview

This charm provides OpenVPN Community VPN (http://openvpn.net/index.php/open-source).
Below is a description taken from the main project site:

OpenVPN is a full-featured open source SSL VPN solution that accommodates a
wide range of configurations, including remote access, site-to-site VPNs,
Wi-Fi security, and enterprise-scale remote access solutions with load
balancing, failover, and fine-grained access-controls.

This charm installs the VPN service and assists in generating user certificates
for connecting to the VPN. Certain configuration settings have been built into
the charm in the form of variables that can be set pre or post installation.
Variables configured pre-installation can be found in the
"Advanced Installation Configuration Settings" section and variables that can
be changed at any point during the charm lifecycle can be found in the
"Common Configuration Settings" section located in this README.

# Usage

To deploy the charm, you will first need a bootstrapped Juju environment and,
at a minimum, capacity for one additional machine.

Deploy openvpn to a bootstrapped environment:

    juju deploy openvpn

Then expose the service:

    juju expose openvpn

# Connecting to the VPN

Once the OpenVPN service is ready, you will need to download the user keys,
certificates, and config generated during installation in order to connect.
The charm creates a tarball with this information whenever a new user is
added and places it in the home directory of the default user. In order to
download the tarball, you must know the machine number the unit is running on
and the name of the user set by Juju (default: "admin"). You can find the
machine number by viewing the output from 'juju status'. Below is an example
of downloading the config for the default user, "admin", from machine "1":

    juju scp 1:~/admin.tgz .

Next extract and view the contents of the files:
    
    tar xzf admin.tgz
    cd admin_keys
    
Finally, install the VPN client and connect to the VPN:
    
    sudo apt-get install openvpn
    sudo openvpn --config client.ovpn

You may wish to daemonize the process or import this config into NetworkManager.
Please consult the OpenVPN documentation located here for further assitence in
configuring the OpenVPN client: http://bit.ly/19R9dP3.

It is a good idea to remove the tarball from the VPN server once you have
downloaded it. You can do so by issuing the commands below:

    juju ssh 1
    sudo rm admin.tgz
    exit

The keys are still retained in '/etc/openvpn/easy-rsa/keys' for later use.

# Configuration

There are a number of configuration options available via the charm. Most options
can be safely left to their default settings, but are available for more advanced
usage.

By default, the charm runs on UDP port 1194 and generates a user certificate for
client "admin". The interface "eth0" is assumed to the be the primary interface
used by the VPN and it's IP subnet is routed by default through the VPN.

## Common Configuration Settings

Below are some of the most common configuration options that can be changed any
time during the lifecycle of the charm.

### User

Specify a user to create a certificate for. If this is a new user, then a new
client certificate is created, tar'ed, and placed in the system default user's
home directory for retrieval. If the user has been previously created, then no
action is performed.

    juju set openvpn user=joesmith
    
### Port

Specify a port to run the VPN service over.

    juju set openvpn port=1194

### Protocol

Specify either UDP or TCP as the protocol used in VPN communications. UDP will
see better performance overall.

    juju set openvpn protocol=udp

## Advanced Configuration Settings

These settings are provided for users who require more granular control over
VPN settings. These settings may also be changed at any time during the
lifecycle of the charm.

### Client Network

The client-network option defines the network used when assigning VPN clients
addresses. If your home or corporate network uses the same range as the set
default, then you may consider changing it to an alternate network range. A
CIDR value is required for the network.

    juju set openvpn client-network=10.11.12.0/25

### Additional Routes

Additional routes can be specified in a comma separated list to instruct the
VPN to route the given networks. This can be helpful when wanting to route only
specific traffic through the VPN. By default, no additional routes are given.

    juju set openvpn additional-routes="1.1.1.0/24, 2.2.2.0/8"

### Reroute Gateway

By default, all client traffic will NOT be routed through the VPN tunnel. To
allow clients to send all traffic through the VPN tunnel, set this to 'True'.

    juju set openvpn reroute-gateway=False

### Reroute DNS

By default, all DNS queries will NOT be routed through the VPN tunnel. To
enable this feature, set the option to 'True'.

    juju set openvpn reroute-dns=False

### DNS Servers

When either reroute-gateway or reroute-dns is set to 'True', a DHCP DNS option
will be pushed to the client, causing the nameserver to change. By default, the
nameservers used are the OpenDNS nameservers, but alternatives can be specified.

    juju set opevpn dns-servers="4.2.2.2, 8.8.8.8"

### Interface

Specify an interface to be used for NAT and access to networks behind the VPN.
The default interface is 'eth0' and should not be changed unless absolutely
certain.

    juju set openvpn interface=eth0

## Advanced Installation Configuration Settings

These settings are only applied during the initial installation of the charm
or an additional unit. Changing these settings after deployment will have no
effect whatsoever. Each example provided details how to use the setting in a
YAML config file for deployment. An example YAML file looks like the following:

    openvpn:
        key: value
        key2: value2
        
A charm can then be deployed with these options using the following:

    juju deploy --config openvpn.yaml openvpn

Note: If a configuration setting listed below needs to be changed, the only way
to do so is to destroy the charm and redeploy. This, however, will nullify any
user certificates previously generated.

### Domain

Specify a domain to use for certificate signing and generation.

    domain: mydomain.tld

### Key Size

Specify the number of bits in the key to create. By default this is set to
1024, although another common key size is 2048 bits.

    key-size: 2048
    
### Key Country

Specify a country location for the key.

    key-country: US
    
### Key Province

Specify a province location for the key.

    key-province: WA
    
### Key City

Specify a city location for the key.

    key-city: Seattle
    
### Key Organization

Specify an organization for the key.

    key-org: IT Dept

# Managing Users

To add users, you can set the 'user' config option to a different value. A more
granular way of managing users is available via the OpenVPN command line tools
located in the '/etc/openvpn/easy-rsa' directory of the VPN server. User
certificates and certificate passwords can be created. An optional CRL can be
managed using these tools as well. For more information, consult the OpenVPN
documentation.

During the lifecycle of the charm, it should be noted that no user certificates
are ever removed. They are left in tact in the '/etc/openvpn/easy-rsa/keys'
directory and can be retrieved from there.

# Upgrade Information

Since the nature of the OpenVPN service is certificate based, upgrading the
charm will only install the latest version of OpenVPN as found in the Ubuntu
repository and run the config-changed hook. An upgrade will not regenerate
server or client certificates.

# Contact Information

Author: NextRevision <notarobot@nextrevision.net>
Report bugs at: http://bugs.launchpad.net/charms/+source/openvpn
Location: http://jujucharms.com/charms/distro/openvpn
