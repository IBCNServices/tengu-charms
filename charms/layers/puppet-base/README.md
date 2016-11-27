# layer-puppet-base

This layer facilitates the installation of puppet pkgs.

## Usage

To use this layer, include `puppet-base`, and add an `options` for puppet-srvc in your layer's `layer.yaml`.

```yaml
# layer.yaml
---
includes:
  - layer:puppet-base

options:
  puppet-base:
    puppet-srvc: db

...
```

`puppet-srvc` is the Puppet service to install. Possible values:

- `master` installs the `puppetserver` package,
- `agent` installs the `puppet-agent` package,
- `db` installs the `puppetdb` package,
- `ca` installs the `puppetserver` package.

Then you can react when the configured puppet services become available in consuming layers.

```python
import os
from charms.reactive import when, when_not, set_state
from charmhelpers.core.templating import render

PUPPET_DB_CONF = '/etc/puppetlabs/puppetdb/conf.d/puppet.conf'


@when('puppet.db.available', 'postgresql.available')
@when_not('puppet.db.configured')
def configure_pgsql(pgsql):

    '''Write out puppetdb config
    '''
    if os.path.exists(PUPPET_DB_CONF):
        os.remove(PUPPET_DB_CONF)
    render(source='puppet.conf',
           target=PUPPET_DB_CONF,
           perms=0o644,
           owner='root'
           ctxt={'PG_CONN': psql.connection_string()})

    set_state('puppet.db.configured')
```

### States

- **puppet.master.available** - This state is emitted once the `puppetserver` package has been installed.
- **puppet.agent.available** - This state is emitted once the `puppet-agent` package has been installed.
- **puppet.db.available** - This state is emitted once the `puppetdb` package has been installed.
- **puppet.ca.available** - This state is emitted once the `puppetserver` package has been installed.

### More info on Puppet
* [Puppetlabs](https://puppet.com/)

### Copyright

- Copyright &copy; 2016 James Beedy <jamesbeedy@gmail.com>
- Copyright &copy; 2016 Merlijn Sebrechts <merlijn.sebrechts@gmail.com>

### License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
