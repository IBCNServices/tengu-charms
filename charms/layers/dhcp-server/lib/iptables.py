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
import subprocess
import re

import netifaces
from netifaces import AF_INET

###############################################################################
#
# PUBLIC METHODS
#
###############################################################################

def update_port_forwards(config):
    """[{
        "public_port": "<public-port>",
        "private_port": "<private_port>",
        "private_ip": "<private_ip>",
        "protocol": "<tcp/udp>"
    }]"""
    comment = 'managed by juju port forward'
    ips = get_ips()
    ruleset = []
    for p_forward in config:
        for ip in ips:
            accept_rule = {
                'dport' : p_forward['public_port'],
                'destination' : ip,
                'jump' : 'ACCEPT',
                'protocol' : p_forward['protocol'],
                'table' : 'filter',
                'chain' : 'FORWARD'
            }
            ruleset.append(accept_rule)
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
    update_rules(ruleset, comment)


def configure_nat_gateway(dhcp_if, public_ifs):
    comment = 'managed by juju nat gateway'
    ruleset = []
    for pub_if in public_ifs:
        ruleset.append({
            'table' : 'nat',
            'chain' : 'POSTROUTING',
            'out-interface' : pub_if,
            'jump' : 'MASQUERADE',
        })
    ruleset.append({
        'table' : 'filter',
        'chain' : 'FORWARD',
        'in-interface' : dhcp_if,
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
    known_options = ['jump', 'protocol', 'in-interface', 'out-interface', 'source', 'destination', 'dport', 'to-destination']
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
        'to' : 'to-destination',
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
