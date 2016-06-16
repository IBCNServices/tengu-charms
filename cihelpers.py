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
# pylint: disable=c0111
import click
import yaml


def replace_charm_url(filename, urls):
    replacers = generate_replacers(urls)
    with open(filename, 'r+') as stream:
        bundle = yaml.load(stream)
        for (key, value) in bundle['services'].items():
            charmname = value['charm'].split('/')[-1]
            candidate = replacers.get(charmname)
            if candidate:
                bundle['services'][key]['charm'] = candidate
        stream.seek(0)
        stream.write(yaml.dump(bundle))
        stream.truncate()

def generate_replacers(urls):
    replacers = dict()
    for url in urls:
        charmname = url.split('/')[-1].rsplit('-', 1)[0]
        replacers[charmname] = url
    return replacers





@click.group()
def g_cli():
    pass

@click.command(name='replace')
@click.argument(
    'path', nargs=1,
    type=click.Path(exists=True, readable=True, writable=True))
@click.argument(
    'urls', nargs=-1)
def c_replace(path, urls):
    """ Print info of configured jfed user """
    replace_charm_url(path, urls)

g_cli.add_command(c_replace)


if __name__ == '__main__':
    g_cli()
