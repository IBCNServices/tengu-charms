#!/usr/bin/python3
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
