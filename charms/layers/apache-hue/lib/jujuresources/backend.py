from contextlib import closing
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile

try:
    # Python 3
    from urllib.parse import urlparse, urljoin, parse_qs
    from hashlib import algorithms_available as hashlib_algs
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from urlparse import urlparse, urljoin, parse_qs
    from hashlib import algorithms as hashlib_algs
    from urllib2 import urlopen


class ALL(object):
    """
    Placeholder to select all resources, optional as well as required.
    """
    pass


class ResourceContainer(dict):
    def __init__(self, output_dir):
        super(ResourceContainer, self).__init__()
        self._required = set()
        self.output_dir = output_dir

    def add_required(self, name, resource):
        self[name] = Resource.get(name, resource, self.output_dir)
        self._required.add(name)

    def add_optional(self, name, resource):
        self[name] = Resource.get(name, resource, self.output_dir)

    def all(self):
        return self.values()

    def required(self):
        return [self[name] for name in self._required]

    def subset(self, which):
        if not which:
            return self.required()
        if which is ALL:
            return self.all()
        if not isinstance(which, (list, tuple)):
            return [self[which]]
        return [self[name] for name in which]


class Resource(object):
    """
    Base class for a Resource.
    Handles local file resources (with explicit ``filename`` or ``destination``).
    """
    @classmethod
    def get(cls, name, definition, output_dir):
        """
        Dispatch to the right subclass based on the definition.
        """
        if 'url' in definition:
            return URLResource(name, definition, output_dir)
        elif 'pypi' in definition:
            return PyPIResource(name, definition, output_dir)
        else:
            return Resource(name, definition, output_dir)

    def __init__(self, name, definition, output_dir):
        self.name = name
        self.source = definition.get('file', '')
        self.filename = os.path.basename(self.source)
        self.destination = definition.get(
            'destination', os.path.join(output_dir, self.filename))
        self.spec = self.destination
        self.hash = definition.get('hash', '')
        self.hash_type = definition.get('hash_type', '')
        self.skip_hash = definition.get('skip_hash', False)
        self.output_dir = output_dir

    def fetch(self, mirror_url=None):
        return

    def verify(self):
        if not os.path.isfile(self.destination):
            return False
        if self.skip_hash:
            return True  # for testing use only
        if self.hash_type not in hashlib_algs:
            return False
        with open(self.destination, 'rb') as fp:
            hash = hashlib.new(self.hash_type)
            for chunk in iter(lambda: fp.read(16*1024), b''):  # read chunks until nothing returned
                hash.update(chunk)
            if self.hash != hash.hexdigest():
                return False
        return True

    def install(self, destination, skip_top_level=False):
        if not self.verify():
            return False
        if not destination:
            raise ValueError('Destination is required for install of: %s' % self.name)

        def filter_members(af):
            members = af.infolist() if hasattr(af, 'infolist') else af
            for member in members:
                if not skip_top_level:
                    yield member
                    continue
                if hasattr(member, 'path'):
                    path = member.path  # tarfiles
                elif hasattr(member, 'filename'):
                    path = member.filename  # zipfiles
                if re.match(r'^[^/]+/?$', path):
                    continue  # skip top-level members
                path = re.sub(r'^[^/]+/', '', path)  # strip top-level container
                if hasattr(member, 'path'):
                    member.path = path  # tarfiles
                elif hasattr(member, 'filename'):
                    member.filename = path  # zipfiles
                yield member

        if not os.path.exists(destination):
            os.makedirs(destination)

        if tarfile.is_tarfile(self.destination):
            with tarfile.open(self.destination) as tf:
                tf.extractall(destination, members=filter_members(tf))
        elif zipfile.is_zipfile(self.destination):
            with zipfile.ZipFile(self.destination, 'r') as zf:
                zf.extractall(destination, members=filter_members(zf))
        elif self._is_bugged_tarfile():
            self._handle_bugged_tarfile(destination, skip_top_level)
        else:
            shutil.copy2(self.destination, destination)
        return True

    def _is_bugged_tarfile(self):
        """
        Check for tar file that tarfile library mistakenly reports as invalid.
        Happens with tar files created on FAT systems.  See:
        http://stackoverflow.com/questions/25552162/tarfile-readerror-file-could-not-be-opened-successfully
        """
        try:
            output = subprocess.check_output(['file', '-z', self.destination]).decode('utf8')
            return 'tar archive' in output and 'gzip compressed data' in output
        except subprocess.CalledProcessError:
            return False

    def _handle_bugged_tarfile(self, destination, skip_top_level):
        """
        Handle tar file that tarfile library mistakenly reports as invalid.
        Happens with tar files created on FAT systems.  See:
        http://stackoverflow.com/questions/25552162/tarfile-readerror-file-could-not-be-opened-successfully
        """
        args = ['tar', '-xzf', self.destination, '-C', destination]
        if skip_top_level:
            args.extend(['--strip-components', '1'])
        subprocess.check_call(args)


class URLResource(Resource):
    def __init__(self, name, definition, output_dir):
        super(URLResource, self).__init__(name, definition, output_dir)
        self.url = definition.get('url', '')
        self.spec = self.url
        self.filename = definition.get(
            'filename', os.path.basename(urlparse(self.url).path))
        self.destination = definition.get(
            'destination', os.path.join(self.output_dir, name, self.filename))

    def fetch(self, mirror_url=None):
        if mirror_url:
            url = urljoin(mirror_url, os.path.join(self.name, self.filename))
        else:
            url = self.url
        if url.startswith('./'):
            url = url[2:]  # urlretrieve complains about this for some reason

        if urlparse(self.hash).scheme:
            hash_url_parts = urlparse(self.hash)
            hash_filename = os.path.basename(hash_url_parts.path)
            hash_url = urljoin(mirror_url, os.path.join(self.name, hash_filename)) if mirror_url else self.hash
            hash_dst = os.path.join(os.path.dirname(self.destination), hash_filename)
            try:
                with closing(urlopen(hash_url)) as hash_in, open(hash_dst, 'w+') as hash_out:
                    hash_out.write(hash_in.read())
                with open(hash_dst) as fp:
                    self.hash = fp.read(8*1024).strip()  # hashes should never be that big
            except IOError as e:
                sys.stderr.write('Error fetching hash {}: {}\n'.format(hash_url, e))
                return  # ignore download errors; they will be caught by verify

        if not os.path.exists(os.path.dirname(self.destination)):
            os.makedirs(os.path.dirname(self.destination))
        if os.path.exists(self.destination):
            os.remove(self.destination)  # urlretrieve won't overwrite
        try:
            with closing(urlopen(url)) as res_in, open(self.destination, 'w+') as res_out:
                res_out.write(res_in.read())
        except IOError as e:
            sys.stderr.write('Error fetching {}: {}\n'.format(self.url, e))
            return  # ignore download errors; they will be caught by verify


class PyPIResource(URLResource):
    def __init__(self, name, definition, output_dir):
        super(PyPIResource, self).__init__(name, definition, output_dir)
        self.spec = definition.get('pypi', '')
        urlspec = urlparse(self.spec)
        if urlspec.scheme:
            self.package_name = parse_qs(re.sub(r'^#', '', urlspec.fragment)).get('egg', [''])[0]
            if '+' in urlspec.scheme:
                # git+https:// URLs are useful for testing and development
                # but need to be handled more like package names than URLs
                # (NB: You'll probably also want to use skip_hash: true because the
                # hashes of the artifacts created from repos tend to always change.)
                self.url = ''
                self.destination_dir = os.path.join(self.output_dir, self.package_name)
                self.filename = ''
                self.destination = ''
            else:
                self.url = self.spec
                self.destination_dir = self.output_dir
                self.filename = os.path.basename(urlspec.path)
                self.destination = os.path.join(self.destination_dir, self.filename)
        else:
            self.url = ''
            self.package_name = re.sub(r'[<>=].*', '', self.spec)
            self.destination_dir = os.path.join(self.output_dir, self.package_name)
            self.filename = ''
            self.destination = ''

    def fetch(self, mirror_url=None):
        if self.url:
            return super(PyPIResource, self).fetch(mirror_url)
        if os.path.exists(self.destination_dir):
            shutil.rmtree(self.destination_dir)  # `pip --download` won't overwrite
        os.makedirs(self.destination_dir)
        cmd = ['pip', 'install', self.spec, '--download', self.destination_dir]
        if mirror_url:
            cmd.extend(['-i', mirror_url])
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:  # noqa
            sys.stderr.write('Error fetching {}:\n{}\n'.format(self.name, e.output))
            return
        if not mirror_url:
            mirror_url = 'https://pypi.python.org/simple'
        mirror_url = mirror_url.rstrip('/') + '/'  # ensure trailing slash
        for filename in os.listdir(self.destination_dir):
            if filename.startswith(self.package_name):
                self.filename = filename
                self.destination = os.path.join(self.destination_dir, filename)
                if not self.hash or not self.hash_type:
                    hash_type, hash = self.get_remote_hash(self.filename, mirror_url)
                    self.hash = hash
                    self.hash_type = hash_type
                    if hash_type:
                        hash_file = '.'.join([self.destination, self.hash_type])
                        self._write_file(hash_file, self.hash + '\n')
            else:
                self.process_dependency(filename, mirror_url)

    def verify(self):
        self.get_local_hash()
        return super(PyPIResource, self).verify()

    def get_local_hash(self):
        if self.skip_hash:
            return
        if self.url:
            return
        if not os.path.isdir(self.destination_dir):
            return
        for filename in os.listdir(self.destination_dir):
            fullname = os.path.join(self.destination_dir, filename)
            for hash_type in hashlib_algs:
                hash_file = '{}.{}'.format(fullname, hash_type)
                if os.path.isfile(hash_file):
                    self.filename = filename
                    self.destination = fullname
                    self.hash_type = hash_type.lower()
                    with open(hash_file) as fp:
                        self.hash = fp.readline().strip()
                    return

    def get_remote_hash(self, filename, mirror_url):
        if self.skip_hash:
            return ('', '')
        package_name = self._package_name_from_filename(filename, mirror_url)
        url = urljoin(mirror_url, package_name)
        link_re = (
            r'href=(?:"(?:[^"]*/)?|\'(?:[^\']*/)?)'
            '{}#([^=]+)=(\w+)["\']'.format(re.escape(filename)))
        try:
            with closing(urlopen(url)) as fp:
                for line in fp:
                    match = re.search(link_re, line)
                    if match:
                        return match.groups()
        except IOError as e:
            sys.stderr.write('Error fetching hash {}: {}\n'.format(url, e))
            return ('', '')

        sys.stderr.write('Hash not found for {}\n'.format(filename))
        return ('', '')

    def process_dependency(self, filename, mirror_url):
        # pip will download all dependencies into the same directory
        # we need to move them to their own package folders to be
        # properly mirrored
        package_name = self._package_name_from_filename(filename, mirror_url)
        new_dir = os.path.join(self.output_dir, package_name)
        old_dest = os.path.join(self.destination_dir, filename)
        new_dest = os.path.join(new_dir, filename)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        os.rename(old_dest, new_dest)
        hash_type, hash = self.get_remote_hash(filename, mirror_url)
        if hash_type:
            hash_file = '.'.join([new_dest, hash_type])
            self._write_file(hash_file, hash + '\n')

    @classmethod
    def _package_name_from_filename(cls, filename, mirror_url):
        # package file names may or may not contain various bits,
        # such as the arch, python version, package version, etc,
        # so we need to figure out what prefix is actually the
        # package name
        index = cls._get_index(mirror_url)
        parts = filename.split('-')
        while parts:
            package_name = '-'.join(parts)
            if package_name in index:
                return package_name
            parts.pop()
        return ''

    @classmethod
    def _get_index(cls, url):
        if not getattr(cls, '_index', None):
            cls._index = set()
            try:
                with closing(urlopen(url)) as fp:
                    for line in fp:
                        matches = re.findall(r'<a href=(?:"[^"]*"|\'[^\']*\')>([^</]+)', line)
                        for project in matches:
                            cls._index.add(project)
            except IOError as e:
                sys.stderr.write('Error fetching index {}: {}\n'.format(url, e))
        return cls._index

    def _write_file(self, filename, text):
        with open(filename, 'w') as fp:
            fp.write(text)

    @classmethod
    def build_pypi_indexes(cls, root_dir):
        for entry in os.listdir(root_dir):
            candidate = os.path.join(root_dir, entry)
            if not os.path.isdir(candidate):
                continue
            res = PyPIResource(entry, {'pypi': entry}, root_dir)
            res.get_local_hash()
            if not res.hash_type:
                continue
            res._write_file(os.path.join(candidate, 'index.html'), '\n'.join([
                '<html>',
                '  <head>',
                '    <title>Links for {}</title>'.format(res.package_name),
                '    <meta name="api-version" value="2" />',
                '  </head>',
                '  <body>',
                '    <h1>Links for {}</h1>'.format(res.package_name),
                '    <a href="{0.filename}#{0.hash_type}={0.hash}" rel="internal">'
                '{0.filename}</h1>'.format(res),
                '  </body>',
                '</html>',
            ]))

    def install(self):
        if not self.verify():
            return False
        return subprocess.call(['pip', 'install', self.destination]) == 0

    @classmethod
    def install_group(cls, resources, mirror_url=None):
        to_install = []
        for resource in resources:
            if resource.verify():
                # use pre-fetched copy, if available
                to_install.append(resource.destination)
            else:
                # otherwise, try installing directly from mirror
                to_install.append(resource.spec)
        cmd = ['pip', 'install'] + to_install
        if mirror_url:
            cmd.extend(['-i', mirror_url])
        return subprocess.call(cmd) == 0
