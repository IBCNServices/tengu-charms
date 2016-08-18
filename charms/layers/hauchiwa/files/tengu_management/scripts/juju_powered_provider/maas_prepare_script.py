#!/usr/bin/env python3
#pylint:disable=c0103,c0111,c0301
import re
import subprocess
from ipaddress import IPv4Network, IPv4Address
upcommands = """
    post-up ip rule add from {interface_ip} table isp2
    post-up ip route add default via {gateway} table isp2
"""
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
            print(GATEWAY)
            filled_in_upcommands = upcommands.format(interface_ip=ip.split('/')[0], gateway=str(GATEWAY))
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
                print(interfaces)
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
assert found
