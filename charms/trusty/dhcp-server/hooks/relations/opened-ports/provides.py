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
        # clear ping so we don't get an endless loop
        self.set_remote('pingpong', '')


    @hook('{provides:opened-ports}-relation-{departed,broken}')
    def broken(self):
        self.remove_state('{relation_name}.available')


    def configure(self):
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
        jsonop = json.dumps(opened_ports)
        self.set_remote(
            'opened-ports', jsonop,
        )
        if self.get_remote('opened-ports', '') == jsonop:
            self.set_state('{relation_name}.ready')


    def forwards(self):
        return json.loads(self.get_remote('opened-ports', '[]'))


    def update(self):
        # Request a ping, remote will return ping causing the relation to run again, causing a configure
        # This is needed because opened-ports only get shown in `opened-ports` after the hook runs
        self.set_remote('pingpong', self.get_remote('pingpong', '') + 'ping')
