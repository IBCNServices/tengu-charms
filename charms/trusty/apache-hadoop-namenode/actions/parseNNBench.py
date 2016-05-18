#!/usr/bin/env python3
"""
Simple script to parse nnbench transaction results
and reformat them as JSON for sending back to juju
"""
import sys
import json
from charmhelpers.core import hookenv
import re


def parse_nnbench_output():
    """
    Parse the output from nnbench and set the action results:

    """

    results = {}

    # Find all of the interesting things
    regex = re.compile('\t+(.*)=(.*)')
    for line in sys.stdin.readlines():
        m = regex.match(line)
        if m:
            results[m.group(1)] = m.group(2)
    hookenv.action_set({"results.raw": json.dumps(results)})

if __name__ == "__main__":
    parse_nnbench_output()
