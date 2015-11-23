#!/usr/bin/python
import os
import shutil
import tarfile
import urllib

def add_line_to_file(line, filepath):
    """appends line to file if not present"""
    filepath = os.path.realpath(filepath)
    if not os.path.isdir(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    found = False
    if os.path.isfile(filepath):
        with open(filepath, 'r+') as myfile:
            lst = myfile.readlines()
        for existingline in lst:
            if line in existingline:
                print "line already present"
                found = True
    if not found:
        myfile = open(filepath, 'a+')
        myfile.write(line+"\n")
        myfile.close()


def append(a_string, filepath):
    """ appends string to file if it is not present.
    Creates file if it doesn't exist."""
    with open(filepath, 'r+') as appendfile:
        content = appendfile.read()
        if a_string not in content:
            appendfile.write(a_string + '\n')


def get_ssh_key(home_dir):
    """Gets in_rsa contents from .ssh folder in given directory"""
    with open('%s/.ssh/id_rsa.pub' % home_dir, 'r') as keyfile:
        data = keyfile.read()
    return data


def set_ssh_key_authorized(key, home_dir):
    """ Puts ssh key in home_dir/.ssh/authorized_keys
    If it isn't already present"""
    with open('%s/.ssh/authorized_keys' % home_dir) as keyfile:
        lst = keyfile.readlines()
    found = False
    for line in lst:
        if key in line:
            print "ssh key already present"
            found = True

    if not found:
        keyfile = open('%s/.ssh/authorized_keys' % home_dir, 'a')
        keyfile.write(key+"\n")
        keyfile.close()

def mergecopytree(src, dst, symlinks=False, ignore=None):
    """"Recursive copy src to dst, mergecopy directory if dst exists.
    OVERWRITES EXISTING FILES!!"""
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if symlinks and os.path.islink(src_item):
            if os.path.lexists(dst_item):
                os.remove(dst_item)
            os.symlink(os.readlink(src_item), dst_item)
        elif os.path.isdir(src_item):
            mergecopytree(src_item, dst_item, symlinks, ignore)
        else:
            shutil.copy2(src_item, dst_item)

def get_proxy():
    """Returns dict with proxy and no_proxy env vars"""
    proxy = os.environ.get('http_proxy')
    no_proxy = os.environ.get('no_proxy')
    return {'proxy':proxy, 'no_proxy':no_proxy}

def downloadbigfiles(path):
    """Downloads url from .source files it finds in path"""
    # The top argument for walk
    topdir = os.path.realpath(path)
    print "downloading sources in %s " % topdir
    # The extension to search for
    exten = '.source'
    for dirpath, dirnames, files in os.walk(topdir):
        for name in files:
            if name.lower().endswith(exten):
                source = os.path.join(dirpath, name)
                file_to_download = source[:-len(exten)]
                print '%s' % file_to_download

                if not os.path.isfile(file_to_download):
                    with open(source, "r") as myfile:
                        url = myfile.readline().rstrip()
                        command = myfile.readline().rstrip()
                    print '\t DOWNLOADING FROM: %s' % url
                    urlopener = urllib.URLopener()
                    urlopener.retrieve(url, file_to_download)
                    if command == "extract":
                        print '\t EXTRACTING: %s' % file_to_download
                        tfile = tarfile.open(file_to_download, 'r')
                        # Important to note that the following extraction is
                        # UNSAFE since .tar.gz archive could contain
                        # relative path like ../../ and overwrite other dirs
                        tfile.extractall(os.path.dirname(file_to_download))
                else:
                    print '\t OK'
                print
