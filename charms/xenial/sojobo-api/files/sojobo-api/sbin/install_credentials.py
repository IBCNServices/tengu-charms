#!/usr/bin/env python3
#pylint: disable=c0111
import subprocess
import yaml   # Should be present after installing Juju

def init():
    subprocess.check_call(['juju'])  # to make sure config folder is present

def merge(a, b):#pylint: disable=c0103
    with open(b, 'r') as b_file:
        cont_dict = yaml.safe_load(b_file.read())
    merge_yaml_file_and_dict(a, cont_dict)

def merge_yaml_file_and_dict(filepath, datadict):
    with open(filepath, 'w+') as e_file:
        filedict = yaml.load(e_file) or {}
        filedict = deep_merge(filedict, datadict)
        e_file.seek(0)  # rewind
        e_file.write(yaml.dump(filedict, default_flow_style=False))

class MergerError(Exception):
    pass

def deep_merge(a, b):#pylint: disable=c0103
    """merges b into a and return merged result

    NOTE: tuples and arbitrary objects are not handled as it is totally
    ambiguous what should happen
    source: https://stackoverflow.com/questions/7204805"""
    key = None
    # ## debug output
    # sys.stderr.write("DEBUG: {} to {}\n".format(b,a))
    try:
        if (a is None or
                isinstance(a, str) or
                isinstance(a, str) or
                isinstance(a, int) or
                isinstance(a, float)):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = deep_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                raise MergerError(
                    'Cannot merge non-dict "{}" into dict "{}"'.format(b, a)
                )
        else:
            raise MergerError('NOT IMPLEMENTED "{}" into "{}"'.format(b, a))
    except TypeError as e: #pylint:disable=c0103
        raise MergerError('TypeError "{}" in key "{}" when merging "{}" \
                           into "{}"'.format(e, key, b, a))
    return a

if __name__ == '__main__':
    init()
    merge('~/.local/share/juju/clouds.yaml', 'clouds.yaml')
    merge('~/.local/share/juju/credentials.yaml', 'credentials.yaml')
    merge('~/.local/share/juju/controllers.yaml', 'controllers.yaml')
