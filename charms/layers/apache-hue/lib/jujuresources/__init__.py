import contextlib
import subprocess

try:
    from urllib.request import urlopen  # Python 3
except ImportError:
    from urllib import urlopen  # Python 2

import yaml

from jujuresources.backend import ResourceContainer
from jujuresources.backend import PyPIResource
from jujuresources.backend import ALL


__all__ = ['fetch', 'verify', 'install', 'resource_path', 'resource_spec',
           'ALL', 'config_get', 'juju_log']
resources_cache = {}


def config_get(option_name):
    """
    Helper to access a Juju config option when charmhelpers is not available.

    :param str option_name: Name of the config option to get the value of
    """
    try:
        raw = subprocess.check_output(['config-get', option_name, '--format=yaml'])
        return yaml.load(raw.decode('UTF-8'))
    except ValueError:
        return None


def juju_log(message, level='DEBUG'):
    """
    Helper to send Juju log messages when charmhelpers is not available.

    :param str message: Message to log
    :param str level: Log level (DEBUG, INFO, ERROR, WARNING, CRITICAL; default: DEBUG)
    """
    subprocess.check_call(['juju-log', '-l', level, message])


def _load(resources_yaml, output_dir=None):
    if (resources_yaml, output_dir) not in resources_cache:
        url = 'file://%s' % resources_yaml if resources_yaml.startswith('/') else resources_yaml
        with contextlib.closing(urlopen(url)) as fp:
            resdefs = yaml.load(fp)
        _output_dir = output_dir or resdefs.get('options', {}).get('output_dir', 'resources')
        resources = ResourceContainer(_output_dir)
        for name, resource in resdefs.get('resources', {}).items():
            resources.add_required(name, resource)
        for name, resource in resdefs.get('optional_resources', {}).items():
            resources.add_optional(name, resource)
        resources_cache[(resources_yaml, output_dir)] = resources
    return resources_cache[(resources_yaml, output_dir)]


def _invalid(resources, which):
    invalid = set()
    for resource in resources.subset(which):
        if not resource.verify():
            invalid.add(resource.name)
    return invalid


def _fetch(resources, which, mirror_url, force=False, reporthook=None):
    invalid = _invalid(resources, which)
    for resource in resources.subset(which):
        if resource.name not in invalid and not force:
            continue
        if reporthook:
            reporthook(resource.name)
        resource.fetch(mirror_url)


def _install(resources, which, mirror_url, destination, skip_top_level):
    success = True
    pypi_resources = []
    for resource in resources.subset(which):
        if isinstance(resource, PyPIResource):
            # group pypi resources to reduce subprocess calls
            pypi_resources.append(resource)
        else:
            success = resource.install(destination, skip_top_level) and success
    if pypi_resources:
        success = PyPIResource.install_group(pypi_resources, mirror_url) and success
    return success


def invalid(which=None, resources_yaml='resources.yaml'):
    """
    Return a list of the names of the resources which do not
    pass :func:`verify`.

    :param list which: A name, or a list of one or more resource names, to
        fetch.  If ommitted, all non-optional resources are verified.
        You can also pass ``jujuresources.ALL`` to fetch all optional *and*
        required resources.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``./resources.yaml``).
        Can be a local file name or a remote URL.
    """
    resources = _load(resources_yaml, None)
    return _invalid(resources, which)


def verify(which=None, resources_yaml='resources.yaml'):
    """
    Verify if some or all resources previously fetched with :func:`fetch_resources`,
    including validating their cryptographic hash.

    :param list which: A list of one or more resource names to
        check.  If ommitted, all non-optional resources are verified.
        You can also pass ``jujuresources.ALL`` to fetch all optional and
        required resources.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``resources.yaml``).
        Can be a local file name or a remote URL.
    :param str output_dir: Override ``output_dir`` option from `resources_yaml`
        (this is intended for mirroring via the CLI and it is not recommended
        to be used otherwise)
    :return: True if all of the resources are available and valid, otherwise False.
    """
    resources = _load(resources_yaml, None)
    return not _invalid(resources, which)


def fetch(which=None, mirror_url=None, resources_yaml='resources.yaml',
          force=False, reporthook=None):
    """
    Attempt to fetch all resources for a charm.

    :param list which: A name, or a list of one or more resource names, to
        fetch.  If ommitted, all non-optional resources are fetched.
        You can also pass ``jujuresources.ALL`` to fetch all optional *and*
        required resources.
    :param str mirror_url: Fetch resources from the given mirror.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``./resources.yaml``).
        Can be a local file name or a remote URL.
    :param force bool: Force re-downloading of valid resources.
    :param func reporthook: Callback for reporting download progress.
        Will be called once for each resource, just prior to fetching, and will
        be passed the resource name.
    :return: True or False indicating whether the resources were successfully
        downloaded.
    """
    resources = _load(resources_yaml, None)
    if reporthook is None:
        reporthook = lambda r: juju_log('Fetching %s' % r, level='INFO')
    _fetch(resources, which, mirror_url, force, reporthook)
    failed = _invalid(resources, which)
    if failed:
        juju_log('Failed to fetch resource%s: %s' % (
            's' if len(failed) > 1 else '',
            ', '.join(failed)
        ), level='WARNING')
    else:
        juju_log('All resources successfully fetched', level='INFO')
    return not failed


def resource_path(resource_name, resources_yaml='resources.yaml'):
    """
    Get the local path for a named resource that has been fetched.

    This may return ``None`` if the local path cannot be determined
    (for example, if the resource has not been fetched yet and needs
    to be resolved).  Even if it returns a path, that path is not
    guaranteed to exist or be valid; you should always confirm that
    a resource is available using :func:`verify` or :func:`fetch`
    before using it.

    :param str resource_name: The name of a resource to resolve.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``./resources.yaml``).
        Can be a local file name or a remote URL.
    """
    resources = _load(resources_yaml, None)
    return resources[resource_name].destination


def resource_spec(resource_name, resources_yaml='resources.yaml'):
    """
    Get the spec for a named resource.  This would be the URL for URL
    resources, the Python package spec for PyPI resources, the full
    path for local file resources, etc.

    :param str resource_name: The name of a resource to resolve.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``./resources.yaml``).
        Can be a local file name or a remote URL.
    """
    resources = _load(resources_yaml, None)
    return resources[resource_name].spec


def install(which=None, mirror_url=None, destination=None, skip_top_level=False,
            resources_yaml='resources.yaml'):
    """
    Install one or more resources.

    The resource(s) will be fetched, if necessary, and different resource
    types are handled appropriately (e.g., PyPI resources are installed
    with ``pip``, archive file resources are extracted, non-archive file
    resources are copied, etc).

    For PyPI resources, this is roughly equivalent to the following::

        pip install `juju-resources resource_spec $resource` -i $mirror_url

    :param list which: A name, or a list of one or more resource names, to
        fetch.  If ommitted, all non-optional resources are installed.
    :param str mirror_url: Fetch resources from the given mirror.
    :param str destination: Destination to which to extract or copy file resources.
    :param bool skip_top_level: When extracting archive file resources, skip
        all members that are at the top level of the archive and instead extract
        all nested members directly into ``destination``.  E.g., an archive
        containing ``foo/bar.txt`` and ``foo/qux/baz.txt`` will be extracted as
        ``destination/bar.txt`` and ``destination/qux/baz.txt``.
    :param str resources_yaml: Location of the yaml file containing the
        resource descriptions (default: ``resources.yaml``).
        Can be a local file name or a remote URL.
    :returns: True if all resources were successfully installed.
    """
    resources = _load(resources_yaml, None)
    return _install(resources, which, mirror_url, destination, skip_top_level)
