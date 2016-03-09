#!/usr/bin/python3
#pylint:disable=c0301, c0325, c0111, c0103
import subprocess
import re

import netifaces
from netifaces import AF_INET


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
            'target' : line[2],
            'protocol' : line[3],
            #'opt' : line[4], # -- Means no options
            'd_ip' : line[8], # destination ip
            #'proto2' : line[9], # no idea what this does
            'table' : table,
            'chain' : chain,
        }
        in_if = line[5]
        out_if = line[6]
        source = line[7]
        if in_if != '*':
            rule['in_if'] = in_if, # Interface the packet comes in
        if out_if != '*':
            rule['out_if'] = out_if, # interface to send the packet to, * means any/no interface
        if source != '0.0.0.0/0':
            rule['source'] = source, # source ip, 0.0.0.0/0 means anywhere
        rules.append(rule)
        # The rest of the line is a list of key-value items seperated by ':'
        for item in line[10:]:
            item = item.split(':', 1)
            if len(item) == 2:
                rules[-1][item[0]] = item[1]
    return rules


def append_rule(rule):
    edit_rule(rule, '-A')

def delete_rule(rule):
    edit_rule(rule, '-D')

def edit_rule(rule, action):
    rule['target'] = rule['target'].upper()
    table = rule['table'].lower()
    chain = rule['chain'].upper()
    command = [
        'iptables', '-t', table, action, chain,
        '-j', rule['target'],
        '-p', rule['protocol']]
    if rule.get('in_if'):
        command += ['-i', rule['in_if']]
    if rule.get('d_ip'):
        command += ['-d', rule['d_ip']]
    if rule.get('dpt'):
        command += ['--dport', rule['dpt']]
    if rule.get('comment'):
        command += ['-m', 'comment', '--comment', rule['comment']]
    if rule['target'] == 'DNAT':
        command += ['--to-destination', '{}'.format(rule['to'])]
    command = [str(i) for i in command]
    print('DEBUG: COMMAND="""{}"""'.format('" "'.join(command)))
    output = subprocess.check_output(command, universal_newlines=True)
    print('DEBUG: OUTPUT="""{}"""'.format('" "'.join(output)))


def update_port_forwards(config):
    """[{
        "public_port": "<public-port>",
        "private_port": "<private_port>",
        "private_ip": "<private_ip>",
        "protocol": "<tcp/udp>"
    }]"""
    ips = get_ips()
    ruleset = []
    for p_forward in config:
        for ip in ips:
            accept_rule = {
                'dpt' : p_forward['public_port'],
                'd_ip' : ip,
                'target' : 'ACCEPT',
                'protocol' : p_forward['protocol'],
                'comment' : 'managed by juju port forward',
                'table' : 'filter',
                'chain' : 'FORWARD'
            }
            ruleset.append(accept_rule)
            forward_rule = {
                'dpt' : p_forward['public_port'],
                'd_ip' : ip,
                'target' : 'DNAT',
                'to' : '{}:{}'.format(p_forward['private_ip'], p_forward['private_port']),
                'protocol' : p_forward['protocol'],
                'comment' : 'managed by juju port forward',
                'table' : 'nat',
                'chain' : 'PREROUTING'
            }
            ruleset.append(forward_rule)
    for rule in ruleset:
        if not rule_exists(rule):
            append_rule(rule)
    for rule in get_rules('nat', 'PREROUTING') + get_rules('filter', 'FORWARD'):
        if rule.get('comment') == 'managed by juju port forward':
            if not contains_rule(rule, ruleset):
                delete_rule(rule)

def prop_equals(prop1, prop2):
    if str(prop1) == str(prop2):
        return True
    elif prop1 is None and prop2 in ['*', '0.0.0.0/0', '--']:
        return True
    elif prop2 is None and prop1 in ['*', '0.0.0.0/0', '--']:
        return True
    return False

def rule_equals(rule1, rule2):
    for key in rule1.keys():
        if not prop_equals(rule1[key], rule2.get(key)):
            return False
    return True

def rule_exists(rule):
    return contains_rule(rule, get_rules(rule['table'], rule['chain']))

def contains_rule(rule, ruleset):
    for existing_rule in ruleset:
        if rule_equals(rule, existing_rule):
            return True
    return False
