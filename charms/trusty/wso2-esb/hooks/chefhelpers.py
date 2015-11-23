#!/usr/bin/python
# pylint: disable=c0111
# pylint: disable=c0301
import json
import os
import shutil
import subprocess
from charmhelpers.core.hookenv import log
from confighelpers import add_line_to_file #pylint: disable=F0401

CHEF_REPO_DIR = '%s/chef-repo' % os.environ['CHARM_DIR']
CHEF_CONFIG_FILE = '/etc/chef/client.rb'
DATABAG_DIR = '%s/data_bags' % CHEF_REPO_DIR


def install_chef_zero():
    log("installing chef")
    try:
        subprocess.check_output(['which', 'knife'])
    except subprocess.CalledProcessError:
        subprocess.check_call(['sudo', 'dpkg', '-i', '%s/files/chef_11.18.12-1_amd64.deb' % os.environ['CHARM_DIR']])


def configure_chef_zero():
    # configure knife http proxy
    if os.environ.get('http_proxy') is not None:
        add_line_to_file('http_proxy "%s"' % os.environ.get('http_proxy'), CHEF_CONFIG_FILE)
        add_line_to_file('knife[:bootstrap_proxy] = "%s"' % os.environ.get('http_proxy'), CHEF_CONFIG_FILE)
    if os.environ.get('https_proxy') is not None:
        add_line_to_file('https_proxy "%s"' % os.environ.get('https_proxy'), CHEF_CONFIG_FILE)
    if os.environ.get('no_proxy') is not None:
        add_line_to_file('no_proxy "%s"' % os.environ.get('no_proxy'), CHEF_CONFIG_FILE)
        add_line_to_file('knife[:bootstrap_no_proxy] =  "%s"' % os.environ.get('no_proxy'), CHEF_CONFIG_FILE)
    # put repository location in config file
    add_line_to_file('chef_repo_path "%s"' % CHEF_REPO_DIR, CHEF_CONFIG_FILE)
    add_line_to_file('cookbook_path "%s/cookbooks"' % CHEF_REPO_DIR, CHEF_CONFIG_FILE)


def install_chef_cookbooks():
    subprocess.check_call(['knife', 'cookbook', 'upload', '--all', '-z', '-c', CHEF_CONFIG_FILE])


def run_recipe(recipe):
    subprocess.check_call(['chef-client', '-z', '-r', "recipe[%s]" % recipe, '-c', CHEF_CONFIG_FILE])


def write_databag(databag_name, data):
    if data.get('id') is None:
        raise Exception("data has to have id value")

    if not os.path.isdir('%s/%s' % (DATABAG_DIR, databag_name)):
        os.makedirs('%s/%s' % (DATABAG_DIR, databag_name))
    with open('%s/%s/%s.json' % (DATABAG_DIR, databag_name, data.get('id')), 'w') as outfile:
        json.dump(data, outfile)


def remove_databag(databag_name):
    if os.path.isdir('%s/%s' % (DATABAG_DIR, databag_name)):
        shutil.rmtree('%s/%s' % (DATABAG_DIR, databag_name))
