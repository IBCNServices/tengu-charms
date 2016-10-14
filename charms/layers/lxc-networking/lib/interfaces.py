#/usr/bin/python3
# print(json.dumps(load(),indent=4))
""" Module to work with `/etc/network/interfaces`"""
from collections import defaultdict

class Interfaces(object):
    """Represents `/etc/network/interfaces`"""
    def __init__(self):
        self.ifs = defaultdict(lambda: {
            'body': [],
        })
        self.other = []


    def load(self):
        """ Parses interfaces file into a dict:
            {
                auto: <auto>,
                iface: <iface>,
                address: <address>,
                netmask: <netmask>,
                bridge_ifaces: <bridge_ifaces>,
                bridge_ports: <bridge_ports>,
                body: [array of other statements],
            }
        """
        auto = []
        curr_stanza = {'body': []}

        with open('/etc/network/interfaces', 'r') as if_file:
            content = if_file.readlines()
        for line in content:
            line = line.lstrip().rstrip()
            splitline = line.split()
            if line == "":
                continue
            if line.startswith('auto'):
                auto.append(splitline[1])
            elif line.startswith(("iface", "mapping", "allow-", "source")): #This line starts a new stanza
                # Commit old stanza
                if curr_stanza['stanza-type'] == "iface":
                    self.ifs[curr_stanza['iface']] = curr_stanza
                else:
                    self.other.append(curr_stanza)
                # Start new stanza

                if line.startswith('iface'):
                    curr_if = splitline[1]
                    curr_stanza = self.ifs[curr_if]
                    curr_stanza['type'] = splitline[2]
                    curr_stanza['method'] = splitline[3]
                else:
                    curr_stanza = {'header': line, 'body': []}
            elif line.startswith(('address', 'netmask', 'bridge_ifaces', 'bridge_ports')):
                curr_stanza[splitline[0]] = line.split(' ', 1)[1]
            else:
                curr_stanza['body'].append(line)
        if curr_stanza['stanza-type'] == "iface":
            self.ifs[curr_stanza['iface']] = curr_stanza
        else:
            self.other.append(curr_stanza)
        for iface in auto:
            self.ifs[iface]['auto'] = True
        return self.ifs


    def write(self):
        """ Write interfaces dict to `/etc/network/interfaces`"""
        content = ""
        for stanza in self.other:
            content += "{}\n".format(stanza['header'])
            for line in stanza['body']:
                content += "{}\n".format(line)
        for iface, value in self.ifs.items():
            if value['auto']:
                content += "auto {}\n".format(iface)
            content += "iface {} {} {}\n".format(iface, value['type'], value['method'])
            for option in ('address', 'netmask', 'bridge_ifaces', 'bridge_ports'):
                if value[option]:
                    content += "    {} {}\n".format(option, value['option'])
            for line in value['body']:
                content += "    {}/n".format(line)
        print(content)


#    with open('/etc/network/interfaces', 'w') as if_file:
#        if_file.write(content)
#        if_file.truncate()




















pass
