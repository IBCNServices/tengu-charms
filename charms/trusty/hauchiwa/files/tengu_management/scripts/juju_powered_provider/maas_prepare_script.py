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

interfaces = subprocess.check_output(['ip link show | cut -d " " -f 2 | sed "s/://" | sed "/^$/d" | grep -v lo'], shell=True, universal_newlines=True).rstrip()
for interface in interfaces.split('\n'):
    interface = interface.split('@')[0]
    ip = subprocess.check_output(["ip addr show {interface} | grep -v secondary | awk '/inet/ && /{interface}/{{print $2}}'".format(interface=interface)], shell=True, universal_newlines=True).rstrip()
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
                assert(match_found)
                m.start()
                m.end()
                interfaces = interfaces[0:m.end()] + filled_in_upcommands + interfaces[(m.end()+1):]
                print(interfaces)
                interfaces_file.seek(0)
                interfaces_file.write(interfaces)
                interfaces_file.truncate()
            subprocess.check_call(["echo 200 isp2 >> /etc/iproute2/rt_tables"], shell=True, universal_newlines=True)
            for command in filled_in_upcommands.rstrip().split("\n"):
                command = command.lstrip(' ').replace('post-up ', "", 1)
                subprocess.check_call([command], shell=True, universal_newlines=True)
            break
