from charms.reactive import scopes
from charms.reactive import RelationBase
from charms.reactive import hook


class MonitoringProvides(RelationBase):
    scope = scopes.UNIT

    @hook('{provides:monitor}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.joined')

    @hook('{provides:monitor}-relation-departed')
    def departed(self):
        self.remove_state('{relation_name}.joined')

    def endpoints(self):
        """
        Returns a list of dicts with information about monitoring services.
        """
        return [{
            'host': conv.get_remote('private-address'),
            'port': 8649,  # currently hard-coded in Ganglia :(
        } for conv in self.conversations()]
