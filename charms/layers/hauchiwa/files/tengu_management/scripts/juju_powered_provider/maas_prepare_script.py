#!/usr/bin/env python3
#pylint:disable=c0103,c0111,c0301
# This script fixes the issue that requests from the internet to the server's
# public ip were being dropped. They were being dropped because the server sends
# the answer through a different interface than the one where the request came
# from. Such packets are being dropped as a security measure.
#
# The cause of this strange behavior is that the default gateway the server gets
# from maas is one in the private network, not on the public network. I first
# tried to force responses to be send out from the same interface.
#    see: https://unix.stackexchange.com/questions/4420/reply-on-same-interface-as-incoming
# This worked for packets destined for the server itself but the combination of
# port-forwards + SNAT + this fix didn't work.
#
# The current fix is to change the default gateway of a server with a public ip.
# This has the disadvantage that the network topology differs between servers
# that have a public ip and those that don't have one.

import re
import subprocess
from ipaddress import IPv4Network, IPv4Address
upcommands = """
    post-up route del default
    post-up route add default gw {gateway}
"""
# This address comes from: http://doc.ilabt.iminds.be/ilabt-documentation/urnsrspecs.html#request-public-ipv4-addresses-for-my-nodes
GATEWAY = IPv4Address('193.190.127.129')

# This script will run in a chroot from the installation environment into the
# actual installed os. This means that the filesystem will be that of the
# installed OS but the kernel is from the installation environment.
# `/etc/network/interfaces` will be that of the installed os but `ifconfig` will
# show the network setup of the installation environment.
#
found = False

interfaces = subprocess.check_output(['cat /etc/network/interfaces | grep iface | cut -d " " -f 2 | grep -v lo'], shell=True, universal_newlines=True).rstrip()
for interface in interfaces.split('\n'):
    interface = interface.split('@')[0]
    # Note: this awk for some reason does not recognize \s
    # Source of this crazy oneliner: https://stackoverflow.com/questions/30300170/get-a-value-from-a-config-file-etc-network-interfaces-for-an-init-d-script/30300241#30300241
    ip = subprocess.check_output(["awk -v par='%s' '/^iface/ && $2==par {f=1} /^iface/ && $2!=par {f=0} f && /^[\\t ]*address/ {print $2; f=0}' /etc/network/interfaces" % interface], shell=True, universal_newlines=True).rstrip()
    if ip:
        print(ip + "wololo")
        network = IPv4Network(ip, strict=False)
        if GATEWAY in network:
            print("Gateway {} is part of network {}.".format(GATEWAY, network))
            filled_in_upcommands = upcommands.format(gateway=str(GATEWAY))
            with open('/etc/network/interfaces', 'r+') as interfaces_file:
                interfaces = interfaces_file.read()
                match_found = False
                matches = re.finditer(r"iface {} .+".format(interface), interfaces)
                m = None
                for m in matches:
                    match_found = True
                assert match_found
                m.start()
                m.end()
                interfaces = interfaces[0:m.end()] + filled_in_upcommands + interfaces[(m.end()+1):]
                print("This is the interfaces file after I changed it: \n{}".format(interfaces))
                interfaces_file.seek(0)
                interfaces_file.write(interfaces)
                interfaces_file.truncate()
            subprocess.check_call(["echo 200 isp2 >> /etc/iproute2/rt_tables"], shell=True, universal_newlines=True)
            # We don't run the commands because we're not actually in that system.
            #for command in filled_in_upcommands.rstrip().split("\n"):
            #    command = command.lstrip(' ').replace('post-up ', "", 1)
            #    subprocess.check_call([command], shell=True, universal_newlines=True)
            found = True
            break
