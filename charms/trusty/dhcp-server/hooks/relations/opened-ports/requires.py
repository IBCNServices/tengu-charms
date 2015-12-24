#pylint:disable=c0111
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class OpenedPortsRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:opened-ports}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('opened-ports'):
            # this unit's conversation has a port, so
            # it is part of the set of available units
            conv.set_state('{relation_name}.available')


    @hook('{requires:opened-ports}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')


    @property
    def opened_ports(self):
        """ Returns list of opened [port, proto] pairs. """
        services = {}
        for conv in self.conversations():
            output = conv.get_remote('opened-ports')
            ports = []
            if output:
                for line in output.split('\n'):
                    port, proto = line.split('/')
                    if '-' in port:
                        first, last = port.split('-')
                        for port in range(first, last):
                            ports.append((port, proto))
                    else:
                        ports.append((port, proto))
            services[conv.get_remote('private-address')] = ports
        return services
