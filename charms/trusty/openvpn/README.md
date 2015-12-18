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

    juju scp openvpn/0:~/client1.tgz .

Next extract and view the contents of the files:

    tar xzf client1.tgz
    cd client1_keys

Finally, install the VPN client and connect to the VPN:

    sudo apt-get install openvpn
    sudo openvpn --config client.ovpn

You may wish to daemonize the process or import this config into NetworkManager.
Please consult the OpenVPN documentation located here for further assitence in
configuring the OpenVPN client: http://bit.ly/19R9dP3.

It is a good idea to remove the tarball from the VPN server once you have
downloaded it. You can do so by issuing the commands below:

    juju ssh openvpn/0
    sudo rm client1.tgz
    exit

The keys are still retained in '/etc/openvpn/easy-rsa/keys' for later use.

# Configuration

There are a number of configuration options available via the charm. Most options
can be safely left to their default settings, but are available for more advanced
usage.

By default, the charm runs on TCP port 443 and generates a user certificate for
client "client1". NAT is enabled on all interfaces (VPN users can connect to all subnets behind those interfaces).

## Common Configuration Settings

Below are some of the most common configuration options that can be changed any
time during the lifecycle of the charm.

### Port

Specify a port to run the VPN service over.

    juju set openvpn port=1194

### Protocol

Specify either UDP or TCP as the protocol used in VPN communications. UDP will
see better performance overall.

    juju set openvpn protocol=udp


## Advanced Installation Configuration Settings

*These settings are only applied during the initial installation of the charm
or an additional unit.* Changing these settings after deployment will have no
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

To add users, you can run `juju action do generate-user username=<name>`

During the lifecycle of the charm, it should be noted that no user certificates
are ever removed. They are left in tact in the '/etc/openvpn/easy-rsa/keys'
directory and can be retrieved from there.

# Upgrade Information

Since the nature of the OpenVPN service is certificate based, upgrading the
charm will only install the latest version of OpenVPN as found in the Ubuntu
repository and run the config-changed hook. An upgrade will not regenerate
server or client certificates.

# Contact Information

Author: Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
Report bugs at: https://github.com/galgalesh/tengu-charms
