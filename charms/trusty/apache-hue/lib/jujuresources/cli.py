from __future__ import print_function
import os
import ssl
import sys
import socket
import argparse
from pkg_resources import iter_entry_points

try:
    # Python 3
    from http.server import SimpleHTTPRequestHandler
    from http.server import HTTPServer
except ImportError:
    # Python 2
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from SocketServer import TCPServer as HTTPServer

from jujuresources import _fetch
from jujuresources import _install
from jujuresources import _invalid
from jujuresources import _load
from jujuresources import ALL
from jujuresources import backend


def arg(*args, **kwargs):
    """
    Decorator to add args to subcommands.
    """
    def _arg(f):
        if not hasattr(f, '_subcommand_args'):
            f._subcommand_args = []
        f._subcommand_args.append((args, kwargs))
        return f
    return _arg


def argset(name, *args, **kwargs):
    """
    Decorator to add sets of required mutually exclusive args to subcommands.
    """
    def _arg(f):
        if not hasattr(f, '_subcommand_argsets'):
            f._subcommand_argsets = {}
        f._subcommand_argsets.setdefault(name, []).append((args, kwargs))
        return f
    return _arg


print = print  # for testing
_exit = sys.exit  # for testing


def resources(argv=sys.argv[1:]):
    """
    Juju CLI subcommand for dispatching resources subcommands.
    """
    eps = iter_entry_points('jujuresources.subcommands')
    ep_map = {ep.name: ep.load() for ep in eps}

    parser = argparse.ArgumentParser()
    if '--description' in argv:
        print('Manage and mirror charm resources')
        return 0

    subparsers = {}
    subparser_factory = parser.add_subparsers()
    subparsers['help'] = subparser_factory.add_parser('help', help='Display help for a subcommand')
    subparsers['help'].add_argument('command', nargs='?')
    subparsers['help'].set_defaults(subcommand='help')
    for name, subcommand in ep_map.items():
        subparsers[name] = subparser_factory.add_parser(name, help=subcommand.__doc__)
        subparsers[name].set_defaults(subcommand=subcommand)
        for args, kwargs in getattr(subcommand, '_subcommand_args', []):
            subparsers[name].add_argument(*args, **kwargs)
        for argset in getattr(subcommand, '_subcommand_argsets', {}).values():
            group = subparsers[name].add_mutually_exclusive_group(required=True)
            for args, kwargs in argset:
                group.add_argument(*args, **kwargs)
    opts = parser.parse_args(argv)
    if opts.subcommand == 'help':
        if opts.command:
            subparsers[opts.command].print_help()
        else:
            parser.print_help()
    else:
        return _exit(opts.subcommand(opts) or 0)


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory to place the fetched resources (default: ./resources/)')
@arg('-u', '--mirror-url',
     help='URL at which the resources are mirrored')
@arg('-a', '--all', action='store_true',
     help='Include all optional resources as well as required')
@arg('-q', '--quiet', action='store_true',
     help='Suppress output and only set the return code')
@arg('-f', '--force', action='store_true',
     help='Force re-download of valid resources')
@arg('-v', '--verbose', action='store_true',
     help='Write download error information to stderr')
@arg('resource_names', nargs='*',
     help='Names of specific resources to fetch (defaults to all required, '
          'or all if --all is given)')
def fetch(opts):
    """
    Create a local mirror of one or more resources.
    """
    resources = _load(opts.resources, opts.output_dir)
    if opts.all:
        opts.resource_names = ALL
    reporthook = None if opts.quiet else lambda name: print('Fetching {}...'.format(name))
    if opts.verbose:
        backend.VERBOSE = True
    _fetch(resources, opts.resource_names, opts.mirror_url, opts.force, reporthook)
    return verify(opts)


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory containing the fetched resources (default: ./resources/)')
@arg('-a', '--all', action='store_true',
     help='Include all optional resources as well as required')
@arg('-q', '--quiet', action='store_true',
     help='Suppress output and only set the return code')
@arg('resource_names', nargs='*',
     help='Names of specific resources to verify (defaults to all required, '
          'or all if --all is given)')
def verify(opts):
    """
    Verify that one or more resources were downloaded successfully.
    """
    resources = _load(opts.resources, opts.output_dir)
    if opts.all:
        opts.resource_names = ALL
    invalid = _invalid(resources, opts.resource_names)
    if not invalid:
        if not opts.quiet:
            print("All resources successfully downloaded")
        return 0
    else:
        if not opts.quiet:
            print("Invalid or missing resources: {}".format(', '.join(invalid)))
        return 1


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory containing the fetched resources (default: ./resources/)')
@arg('-u', '--mirror-url',
     help='URL at which the resources are mirrored')
@arg('-a', '--all', action='store_true',
     help='Include all optional resources as well as required')
@arg('-q', '--quiet', action='store_true',
     help='Suppress output and only set the return code')
@arg('-D', '--destination',
     help='Destination for archive or file resources to be installed to')
@arg('-s', '--skip-top-level', action='store_true',
     help='Skip top-level members of archives, and extract children directly to destination')
@arg('resource_names', nargs='*',
     help='Names of specific resources to verify (defaults to all required, '
          'or all if --all is given)')
def install(opts):
    """
    Install one or more resources.
    """
    resources = _load(opts.resources, opts.output_dir)
    if opts.all:
        opts.resource_names = ALL
    success = _install(resources, opts.resource_names, opts.mirror_url,
                       opts.destination, opts.skip_top_level)
    if success:
        if not opts.quiet:
            print("All resources successfully installed")
        return 0
    else:
        if not opts.quiet:
            invalid = _invalid(resources, opts.resource_names)
            print("Unable to install some resources: {}".format(', '.join(invalid)))
        return 1


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory containing the fetched resources (default: ./resources/)')
@arg('resource_name', help='Name of a resource')
def resource_path(opts):
    """
    Return the full path to a named resource.
    """
    resources = _load(opts.resources, opts.output_dir)
    if opts.resource_name not in resources:
        sys.stderr.write('Invalid resource name: {}\n'.format(opts.resource_name))
        return 1
    print(resources[opts.resource_name].destination)


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory containing the fetched resources (default: ./resources/)')
@arg('resource_name', help='Name of a resource')
def resource_spec(opts):
    """
    Return the spec (URL, package spec, file, etc) for a named resource.
    """
    resources = _load(opts.resources, opts.output_dir)
    if opts.resource_name not in resources:
        sys.stderr.write('Invalid resource name: {}\n'.format(opts.resource_name))
        return 1
    print(resources[opts.resource_name].spec)


@arg('-r', '--resources', default='resources.yaml',
     help='File or URL containing the YAML resource descriptions (default: ./resources.yaml)')
@arg('-d', '--output-dir', default=None,
     help='Directory containing the fetched resources (default: ./resources/)')
@arg('-H', '--host', default='',
     help='IP address on which to bind the mirror server')
@arg('-p', '--port', type=int, default=8080,
     help='Port on which to bind the mirror server')
@arg('-s', '--ssl-cert', default=None,
     help='Path to an SSL certificate file (will run without SSL if not given)')
def serve(opts):
    """
    Run a light-weight HTTP server hosting previously mirrored resources
    """
    resources = _load(opts.resources, opts.output_dir)
    opts.output_dir = resources.output_dir  # allow resources.yaml to set default output_dir
    if not os.path.exists(opts.output_dir):
        sys.stderr.write("Resources dir '{}' not found.  Did you fetch?\n".format(opts.output_dir))
        return 1
    backend.PyPIResource.build_pypi_indexes(opts.output_dir)
    os.chdir(opts.output_dir)

    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer((opts.host, opts.port), SimpleHTTPRequestHandler)

    if opts.ssl_cert:
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=opts.ssl_cert, server_side=True)

    print("Serving at: http{}://{}:{}/".format(
        's' if opts.ssl_cert else '', socket.gethostname(), opts.port))
    httpd.serve_forever()
