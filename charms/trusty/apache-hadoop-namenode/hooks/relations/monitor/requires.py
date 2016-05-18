from charms.reactive import scopes
from charms.reactive import RelationBase
from charms.reactive import hook


class MonitoringRequires(RelationBase):
    scope = scopes.UNIT

    @hook('{requires:monitor}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.joined')

    @hook('{requires:monitor}-relation-departed')
    def departed(self):
        self.remove_state('{relation_name}.joined')

    def endpoints(self):
        """
        Returns a list of host addresses.
        """
        return [conv.get_remote('private-address')
                for conv in self.conversations()]
