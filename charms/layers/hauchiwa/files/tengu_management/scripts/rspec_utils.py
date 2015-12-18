"""
Wrapper around jFed_CLI tool
See http://doc.ilabt.iminds.be/jfed-documentation/cli.html
"""
# pylint:disable=c0301,c0111
import subprocess
from lxml import etree
# Own modules
from output import okblue # pylint: disable=F0401
from jinja2 import Environment, FileSystemLoader
import os

def create_rspec(nr_nodes, userkeys, pub_ipv4, testbed):
    env = Environment(
        loader=FileSystemLoader('{}/../templates/'.format(os.path.dirname(__file__)))
    )
    pub_ipv4 = int(pub_ipv4)
    nr_nodes = int(nr_nodes)
    template = env.get_template('template.rspec')
    component_manager_id = "urn:publicid:IDN+{}.ilabt.iminds.be+authority+cm".format(testbed)
    sliver_type = "raw-pc"
    disk_image = "urn:publicid:IDN+{}.ilabt.iminds.be+image+emulab-ops:UBUNTU14-64-STD".format(testbed)
    nodes = []
    for nodenr in range(nr_nodes):
        nodes.append({
            'name' : 'node{}'.format(nodenr),
            'component_manager_id' : "urn:publicid:IDN+{}.ilabt.iminds.be+authority+cm".format(testbed),
            'sliver_type' : sliver_type,
            'disk_image' : disk_image,
            'private_ip' : "192.168.14.{}".format(nodenr+1),
            'private_netmask' : "255.255.255.0",
            'pubipv4' : (nodenr == 0 and pub_ipv4),
        })
    output = template.render(
        nodes=nodes,
        userkeys=userkeys,
        network_componentmanager=component_manager_id,
        pub_ipv4=pub_ipv4,
    )
    return output

def add_pubkey_to_rspec(xml_filepath, username, pubkey):
    """ Add pubkey to rspec if not present """
    fqdn_user = "urn:publicid:IDN+example.com+user+" + username
    # use a parser that removes non-data whitespace so pretty_print will work
    # when re-serializing the tree
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(xml_filepath, parser)
    root = tree.getroot()
    # Check if key present. And yes, this could be faster with xpath.
    # Feel free to rewrite if you hate xpath less than I do.
    for f_user_ssh_key in root.findall(\
        '{http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1}user-ssh-keys'):
        if f_user_ssh_key.attrib['user'] == fqdn_user:
            for f_ssh_key in f_user_ssh_key.findall(\
                "{http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1}sshkey"):
                if f_ssh_key.text == pubkey:
                    okblue("ssh key already present")
                    return
    # Make required elements and add them
    user_ssh_keys = etree.Element(\
        "{http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1}user-ssh-keys")
    user_ssh_keys.attrib['user'] = \
        fqdn_user
    root.append(user_ssh_keys)
    sshkey = etree.Element(\
        "{http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1}sshkey")
    sshkey.text = pubkey
    user_ssh_keys.append(sshkey)

    with open(xml_filepath, 'w') as outfile:
        tree.write(outfile, pretty_print=True)


def get_manifest_from_host(hostname, username, manifestpath):
    """ Get manifest from host and write it to given path. This is done by
    ssh-ing into the host"""
    manifestfile = open(manifestpath, 'w+')
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(self.environment_config.data)
    # print self.environment_config.config_path
    # if bootstrap-host exists, get manifest from bootstrap-host
    c_command = "ssh"
    c_server = username + "@" + hostname
    c_remote_command = 'geni-get manifest'
    subprocess.check_call([c_command, c_server, c_remote_command],
                          stdout=manifestfile,
                          stderr=subprocess.PIPE)


def get_fqdn(nodename, manifestpath):
    """ Get fqdn of node with given nodename """
    namespaces = {'ns': 'http://www.geni.net/resources/rspec/3'}
    tree = etree.parse(manifestpath)
    root = tree.getroot()
    for at_type in root.findall('.//ns:node[@client_id="' + nodename\
                               + '"]/ns:services/ns:login', namespaces):
        return at_type.get('hostname')


def get_machines(manifestpath):
    """ Return a list with fqdn of nodes in manifest """
    namespaces = {'ns': 'http://www.geni.net/resources/rspec/3'}
    tree = etree.parse(manifestpath)
    root = tree.getroot()
    result = list()

    for at_type in root.findall('.//ns:node/ns:services/ns:login', namespaces):
        if at_type.get('hostname') not in result:
            result.append(at_type.get('hostname'))
    return result


def get_pub_ipv4(manifestpath):
    """ Return a list of dicts that represent the public routable ips

        format: [
            {'address' : '<address1>', 'netmask' : '<netmask1>'},
            {'address' : '<address2>', 'netmask' : '<netmask2>'},
        ]
    """
    ips = []
    namespaces = {
        'ns': 'http://www.geni.net/resources/rspec/3',
        'emulab': 'http://www.protogeni.net/resources/rspec/ext/emulab/1'
    }
    tree = etree.parse(manifestpath)
    root = tree.getroot()
    for ip in root.findall('.//emulab:routable_pool/emulab:ipv4', namespaces): # pylint: disable=c0103
        ips.append({
            'address' : ip.get('address'),
            'netmask' : ip.get('netmask'),
        })
    return ips
