#!/usr/bin/python3
# Copyright (C) 2016  Ghent University
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
#pylint:disable=c0301, c0325, c0111, c0103
import re
import socket
import subprocess

import netifaces
from netifaces import AF_INET

###############################################################################
#
# PUBLIC METHODS
#
###############################################################################

def update_port_forwards(config):
    """ Forward one of our ports to another server.

    config format:
    [{
        "public_port": "<public-port>",
        "private_port": "<private_port>",
        "private_ip": "<private_ip>",
        "protocol": "<tcp/udp>"
    }]"""
    #
    # terminology:
    #   - client: entity that sends the packet to us.
    #   - server: entity that has to receive the packet.
    # When a client connects to one of our forwarded ports, the client thinks
    # it is communicating with is, while it is actually communicating with a
    # server on our managed network.
    # We forward all traffic that we receive on $public_port to the server at
    # $private_ip:$private_port. We forward all answers from the server to the
    # client.
    #   - The client doesn't know how to reach the server, so we need to rewrite
    #     the source ip of the answers the server sends.
    #   - The server needs to respond via us, not via his default gateway, so we
    #     need to rewrite the source address of the packets the client sends us
    #     and the destination address of the packets the server sends us.
    #
    comment = 'managed by juju port forward'
    ips = get_ips()
    ruleset = []
    for p_forward in config:
        for ip in ips:
            # Accept traffic from all our public interfaces to the port
            accept_rule = {
                'dport' : p_forward['public_port'],
                'destination' : ip,
                'jump' : 'ACCEPT',
                'protocol' : p_forward['protocol'],
                'table' : 'filter',
                'chain' : 'FORWARD'
            }
            ruleset.append(accept_rule)
            # Translate the packet's destination IP (us) to the IP of the server
            # that has to receive the packet.
            forward_rule = {
                'dport' : p_forward['public_port'],
                'destination' : ip,
                'jump' : 'DNAT',
                'to-destination' : '{}:{}'.format(p_forward['private_ip'], p_forward['private_port']),
                'protocol' : p_forward['protocol'],
                'table' : 'nat',
                'chain' : 'PREROUTING'
            }
            ruleset.append(forward_rule)
        # Change the source to of packets the clients sends to our ip in the
        # Managed network. This is so the response to this packet will be send
        # to us instead of directly to the source. This is useful when the
        # client won't route the response to us. That scenario can happen when.
        #  - We are not the server's default gateway
        #  - The client and server are on the same network
        #  - The server knows of a different route to the client
        #
        # To do this, we first have to know the IP of the interface that the
        # packed will be send from.
        our_private_ip = get_source_ip(p_forward['private_ip'], p_forward['private_port'], p_forward['protocol'])
        # Then we make the rule
        translate_source_rule = {
            'table' : 'nat',
            'chain' : 'POSTROUTING',
            'protocol' : p_forward['protocol'],
            'destination' : p_forward['private_ip'],
            'dport' : p_forward['private_port'],
            'jump' : 'SNAT',
            'to-source' : our_private_ip,
        }
        ruleset.append(translate_source_rule)
    update_rules(ruleset, comment)


def configure_nat_gateway(private_if, public_ifs):
    """ Act as a NAT gateway """
    comment = 'managed by juju nat gateway'
    ruleset = []
    # Change the source address of packets that
    # - we routed
    # - and are going out to a public interface
    # to our own IP address.
    #
    # I assume that all packets that we routed are coming from IP's that are
    # unknown to clients on our public side. We change the source address of
    # those packets to ourself so the clients will send their answers through us
    # instead of trying to connect directly to the clients.
    for pub_if in public_ifs:
        ruleset.append({
            'table' : 'nat',
            'chain' : 'POSTROUTING',
            'out-interface' : pub_if,
            'jump' : 'MASQUERADE',
        })
    # Accept packets from the private interface that have to be routed.
    ruleset.append({
        'table' : 'filter',
        'chain' : 'FORWARD',
        'in-interface' : private_if,
        'jump' : 'ACCEPT',
    })
    update_rules(ruleset, comment)


def remove_nat_gateway_config():
    comment = 'managed by juju nat gateway'
    ruleset = []
    update_rules(ruleset, comment)


###############################################################################
#
# INTERNAL METHODS
#
###############################################################################

def update_rules(ruleset, comment):
    """
        Update iptables rules to match 'ruleset':

        - All rules from ruleset that are not present in iptables will be added to iptables.
        - All existing rules from iptables that have matching 'comment' but are not in ruleset will be removed from iptables
        - Ruleset gets persisted so all rules will be active after reboot
    """
    rules_changed = False
    # Add all rules that don't exist yet
    ruleset = [standardize_rule(rule) for rule in ruleset]
    for rule in ruleset:
        rule['comment'] = comment
        if not rule_exists(rule):
            rules_changed = True
            append_rule(rule)
    # Get all existing rules
    tables_chain_pairs = (
        ('filter', 'INPUT'),
        ('filter', 'FORWARD'),
        ('filter', 'OUTPUT'),
        ('nat', 'PREROUTING'),
        ('nat', 'POSTROUTING'),
        ('nat', 'OUTPUT'),
    )
    existing_rules = []
    for table, chain in tables_chain_pairs:
        existing_rules.extend(get_rules(table, chain))
    # Remove existing rules that aren't in the ruleset
    for existing_rule in existing_rules:
        if existing_rule.get('comment') == comment:
            if not contains_rule(existing_rule, ruleset):
                rules_changed = True
                delete_rule(existing_rule)
    # persist rules if they changed
    if rules_changed:
        subprocess.check_call(['invoke-rc.d', 'iptables-persistent', 'save'])


def get_ips():
    ips = []
    for interface in netifaces.interfaces():
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet:
            for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                ips.append(link['addr'])
    return ips


def get_rules(table, chain):
    def extract_comment(line):
        start = '/* '
        end = ' */'
        regex = re.compile('({}.*{})'.format(re.escape(start), re.escape(end)))
        result = regex.search(line)
        if result:
            comment = result.group(1).lstrip(start).rstrip(end)
            line = regex.sub('', line)
        else:
            comment = None
        return [comment, line]
    table = table.lower()
    chain = chain.upper()
    rules = []
    output = subprocess.check_output(['iptables', '-t', table, '-L', chain, '--numeric', '--verbose'], universal_newlines=True)
    lines = output.split('\n')[2:][:-1]
    for line in lines:
        (comment, line) = extract_comment(line)
        line = line.split()
        rule = {
            'comment' : comment,
            'jump' : line[2],
            'protocol' : line[3],
            #'opt' : line[4], # -- Means no options
            'in-interface' : line[5],
            'out-interface' : line[6],
            'source' : line[7], # destination ip
            'destination' : line[8], # destination ip
            #'proto2' : line[9], # no idea what this does
            'table' : table,
            'chain' : chain,
        }
        # The rest of the line is a list of key-value items seperated by ':'
        # not-key-value items will be ignored
        for item in line[10:]:
            item = item.split(':', 1)
            if len(item) == 2:
                rule[item[0]] = item[1]
        rules.append(standardize_rule(rule))
    return rules

def append_rule(rule):
    edit_rule(rule, '-A')

def delete_rule(rule):
    edit_rule(rule, '-D')

def edit_rule(rule, action):
    rule = standardize_rule(rule)
    command = [
        'iptables', '-t', rule['table'], action, rule['chain']]
    known_options = ['jump', 'protocol', 'in-interface', 'out-interface', 'source', 'destination', 'dport', 'to']
    for option in known_options:
        if rule.get(option):
            command += ['--{}'.format(option), rule[option]]
    if rule.get('comment'):
        command += ['-m', 'comment', '--comment', rule['comment']]
    print('DEBUG: COMMAND="""{}"""'.format('" "'.join(command)))
    output = subprocess.check_output(command, universal_newlines=True)
    print('DEBUG: OUTPUT="""{}"""'.format('" "'.join(output)))

def standardize_rule(rule):
    rule['jump'] = rule['jump'].upper()
    rule['table'] = rule['table'].lower()
    rule['chain'] = rule['chain'].upper()
    clean_rule = {}
    key_translations = {
        'to-destination' : 'to',
        'to-source' : 'to',
        'dpt' : 'dport',
    }
    for key, value in rule.items():
        # These values are equal to no value, so just skip them
        if value in ['*', '0.0.0.0/0', '--', 'all']:
            continue
        # Translate keys to standardized name
        key = key_translations.get(key, key)
        # Ensure values are string
        value = str(value)
        # Add to clean rule
        clean_rule[key] = value
    return clean_rule

def rule_exists(rule):
    return contains_rule(rule, get_rules(rule['table'], rule['chain']))

def contains_rule(rule, ruleset):
    for existing_rule in ruleset:
        if rule_equals(rule, existing_rule):
            return True
    return False

def rule_equals(rule1, rule2):
    for key in rule1.keys():
        if not rule1[key] == rule2.get(key, None):
            return False
    return True


def get_source_ip(host, port, protocol, recursive=True):
    port = int(port)
    if protocol == "tcp":
        protocol = socket.SOCK_STREAM
    else:
        protocol = socket.SOCK_DGRAM
    sock = socket.socket(socket.AF_INET, protocol)
    sock.settimeout(10)
    try:
        sock.connect((host, port))
    except (ConnectionRefusedError, socket.timeout):
        # It doesn't matter if we were actually able to connect. We just want to
        # know what source IP the OS tried to use to connect.
        # Note: port-forward won't work if we can't connect at this phase, but
        # crashing here seems a bit overkill.
        print("Failed to connect to {}:{}, but will continue anyways.".format(host, port))
    source_ip = sock.getsockname()[0]
    sock.close()
    if source_ip == "0.0.0.0" and recursive:
        print("Source IP == 0.0.0.0. Will try default gateway source ip.")
        source_ip = get_gateway_source_ip()
    print("Got IP = {}".format(source_ip))
    assert(source_ip != "0.0.0.0")
    return source_ip


def get_gateway_source_ip():
    return get_source_ip("8.8.8.8", 80, 'udp', recursive=False)
