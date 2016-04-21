# Apt layer

The Apt layer for Juju enables layered charms to more easily deal with
deb packages and apt sources in a simple and efficient manner. It
provides consistent configuration for operators, allowing them to
easily specify custom apt sources and additional debs required for
their particular installations.

## Configuration

The charm may provide defaults for these service configuration
(config.yaml) options, and the operator may override them as required.

* `extra_packages`

  A space separated list of additional deb packages to install on
  each unit.

* `package_status`

  'install' or 'hold'. When set to hold, packages installed using
  the Apt layer API will be pinned, so that they will not be
  automatically upgraded when package updates are performed. 'hold'
  is particularly useful for allowing a service such as Landscape
  to automatically apply security updates to most of the system,
  whilst holding back any potentially service affecting updates.

* `install_sources`

  A list of apt sources containing the packages that need to be installed.
  Each source may be either a line that can be added directly to
  sources.list(5), or in the form ppa:<user>/<ppa-name> for adding
  Personal Package Archives, or a distribution component to enable.
  The list is a yaml list, encoded as a string. The nicest way of
  declaring this in a yaml file looks like the following (in particular,
  the | character indicates that the value is a multiline string):

  ```yaml
  install_sources: |
      - ppa:stub/cassandra
      - deb http://www.apache.org/dist/cassandra/debian 21x main
  ```

* `install_keys`

  A list of GPG signing keys to accept. There needs to be one entry
  per entry in install_sources. null may be used if no keep is
  needed, which is the case for PPAs and for the standard Ubuntu
  archives. Keys should be full ASCII armoured GPG public keys.
  GPG key ids are also accepted, but in most environments this
  mechanism is not secure. The install_keys list, like
  install_sources, must also be a yaml formatted list encoded as
  a string:

  ```yaml
  install_keys: |
      - null
      - |
          -----BEGIN PGP PUBLIC KEY BLOCK-----
          Version: GnuPG v1

          mQINBFQJvgUBEAC0KcYCTj0hd15p4fiXBsbob0sKgsvN5Lm7N9jzJWlGshJ0peMi
          kH8YhDXw5Lh+mPEHksL7t1L8CIr1a+ntns/Opt65ZPO38ENVkOqEVAn9Z5sIoZsb
          AUeLlJzSeRLTKhcOugK7UcsQD2FHnMBJz50bxis9X7pjmnc/tWpjAGJfaWdjDIo=
          =yiQ4
          -----END PGP PUBLIC KEY BLOCK-----
  ```

## Usage

Queue packages for installation, and have handlers waiting for
these packages to finish being installed:

```python
import charms.apt

@hook('install')
def install():
    charms.apt.queue_install(['git'])

@when_not('apt.installed.gnupg')
def install_gnupg():
    charms.apt.queue_install(['gnupg'])

@when('apt.installed.git')
@when('apt.installed.gnupg')
def grabit():
    clone_repo()
    validate_repo()
```

### API

Several methods are exposed in the charms.apt Python package.

* `add_source(source, key=None)`

  Add an apt source.

  A source may be either a line that can be added directly to
  sources.list(5), or in the form ppa:<user>/<ppa-name> for adding
  Personal Package Archives, or a distribution component to enable.

  The package signing key should be an ASCII armoured GPG key. While
  GPG key ids are also supported, the retrieval mechanism is insecure.
  There is no need to specify the package signing key for PPAs or for
  the main Ubuntu archives.

  It is preferable if charms do not call this directly to hard
  coded apt sources, but instead have these sources listed
  as defaults in the install_sources config option. This allows
  operators to mirror your packages to internal archives and
  deploy your charm in environments without network access.

  Sets the `apt.needs_update` reactive state.

* `queue_install(packages, options=None)`

  Queue one or more deb packages for install. The actual package
  installation will be performed later by a handler in the
  apt layer. The `apt.installed.{name}` state will be set once
  the package installed (one state for each package).

  If a package has already been installed it will not be reinstalled.

  If a package has already been queued it will not be requeued, and
  the install options will not be changed.

* `installed()`

  Returns the set of deb packages installed by this layer.

* `purge(packages)`

  Purge one or more deb packages from the system


### Extras

These methods are called automatically by the reactive framework as
reactive state demands. However, you can also invoke them directly
if you want the operation done right now.

* `update()`

  Update the apt cache. Removes the `apt.needs_update` state.


* `install_queued()`

  Installs deb packages queued for installation. On success, removes
  the `apt.queued_installs` state, sets the `apt.installed.{packagename}`
  state for each installed package, and returns True. On failure,
  sets the unit workload status to blocked and returns False.
  The package installs remain queued.


## Support

This layer is maintained on Launchpad by
Stuart Bishop (stuart.bishop@canonical.com).

Code is available using git at git+ssh://git.launchpad.net/layer-apt.

Bug reports can be made at https://bugs.launchpad.net/layer-apt.

Queries and comments can be made on the Juju mailing list, Juju IRC
channels, or at https://answers.launchpad.net/layer-apt.
