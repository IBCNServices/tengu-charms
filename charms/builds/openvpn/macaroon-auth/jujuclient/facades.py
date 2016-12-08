class BaseFacade(object):
    tag = 'Tag'

    def __init__(self, env, version=None):
        self.env = env
        if version is None:
            version = self.versions[-1]
        self.version = version
        self.tag_prefixes = ["action", "charm", "disk", "machine", "network",
                             "relation", "service", "unit", "user"]

    def _format_tag(self, name):
        return {self.tag: self._format_tag_name(name)}

    def _format_tag_name(self, name):
        for n in self.tag_prefixes:
            if name.startswith("%s-" % n):
                return name
        if name.isdigit():
            return "machine-%s" % name
        if name.startswith('cs:') or name.startswith('local:'):
            return "charm-%s" % name
        if '/' in name:
            return "unit-%s" % name
        if '@' in name:
            return "user-%s" % name
        else:
            raise ValueError("Could not guess entity tag for %s" % name)

    def _format_user_names(self, names):
        """reformat a list of usernames as user tags."""
        if not isinstance(names, (list, tuple)):
            names = [names]
        r = []
        for n in names:
            n = self._format_user_tag(n)
            r.append({self.tag: n})
        return r

    def _format_user_tag(self, n):
        if not n.startswith('user-'):
            n = "user-%s" % n
        if '@' not in n:
            n = "%s@local" % n
        return n

    def _prepare_strparams(self, d):
        r = {}
        for k, v in list(d.items()):
            r[k] = str(v)
        return r

    def _prepare_constraints(self, constraints):
        for k in ['cpu-cores', 'cpu-power', 'mem']:
            if constraints.get(k):
                constraints[k] = int(constraints[k])
        return constraints

    def _prepare_placement(self, placement):
        if ':' in placement:
            scope, directive = placement.split(':')
        else:
            # Assume that the placement is to a machine number
            scope = '#'
            directive = placement
        return {
            "scope": scope,
            "directive": str(directive)
        }

    def rpc(self, op):
        return self.env._rpc(self.check_op(op))

    def check_op(self, op):
        raise NotImplementedError()
