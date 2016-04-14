# python3 pylint:disable=c0111
import subprocess
import json

from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class OpenedPortsProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:opened-ports}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.available')
        self.configure()


    @hook('{provides:opened-ports}-relation-{departed,broken}')
    def broken(self):
        self.remove_state('{relation_name}.available')


    def configure(self):
        conv = self.conversation()
        output = subprocess.check_output(['opened-ports'], universal_newlines=True)
        opened_ports = []
        for line in output.split('\n'):
            if line.rstrip() != '':
                port, protocol = line.split('/')
                if '-' in port:
                    # If port is actually a range, add each port in the range
                    first, last = port.split('-')
                    for port in range(first, last):
                        opened_ports.append({
                            "port": port,
                            "protocol": protocol,
                        })
                else:
                    # If port is not a range, add the port
                    opened_ports.append({
                        "port": port,
                        "protocol": protocol,
                    })
        if opened_ports != conv.get_local('opened_ports', {}):
            jsonop = json.dumps(opened_ports)
            conv.set_remote(
                'opened-ports', jsonop,
            )
            conv.set_local('opened_ports', opened_ports)
        port_forwards = json.loads(self.get_remote('port-forwards', '[]'))
        f_port_set = set(i['private_port'] for i in port_forwards)
        o_ports_set = set(i['port'] for i in opened_ports)
        if f_port_set == o_ports_set:
            self.set_state('{relation_name}.ready')
        else:
            self.remove_state('{relation_name}.ready')


    @property
    def forwards(self):
        return json.loads(self.get_remote('port-forwards', '[]'))
