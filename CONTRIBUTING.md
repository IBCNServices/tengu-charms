# Best practices for contributing to Tengu

Always use the reactive framework and layers when creating a new Charm. Create a **separate repository for each layer and bundle**. Create a **submodule** in `/bundles` pointing to the bundle repo and create a submodule in `/charms/layers` pointing to the layer repo. Build the charm to `/charms/builds` and commit the built charm to this repo.

## General

### Be lazy

Use the charmhelpers library, use existing layers, use existing python libraries.

### Be nice to upstream

When you patch existing code, submit the patches upstream so we can throw away our fork when the patches are merged. Every fork you avoid is time we save.

### Let the users be lazy

Less config options is better. Remove unimportant config options such as the installation directory. If the Charm can find out what the best option is at runtime, do that.

### Say **why** you do something

**Don't bother writing comments about what you're doing. We can all read the code.**

Did you just spend the last 4 hours finding the source of a strange intermittent bug? Write a small comment next to the fix to say why that line is critical because if you don't, you'll forget and remove the line in 5 months.

## Charming

### Change config non-destructively (avoid using templates)

Instead of using templates that completely overwrite existing config files, change them inline. This has a few advantages:

1. **Multiple handlers, layers and users can change a config file.** As long as they don't change the same values, this won't be a problem. Some users want to tweak config files that are managed by a Charm manually. This isn't possible if you use templates.
2. **It's more robust.** We don't have to update the template when a new version of the application has different default config values.

*A handy function for non-destructive editing of config files is the [`re_edit_in_place`](https://pythonhosted.org/jujubigdata/api/jujubigdata.utils.html?highlight=re_edit_in_place#jujubigdata.utils.re_edit_in_place) function of jujubigdata utils*

### More rules

- NO PEP8 ERRORS!!!
- No Linter errors and no `charm proof` errors.
- Always use the `check_..` subprocess functions. If error exit code doesn't matter, catch the exception.
- Don't use `shell=True` for subprocess commands.
- Use upstart on trusty and systemd on xenial to start and stop services.
- use `format` instead of `%` for formatting strings. [Source](http://stackoverflow.com/a/12382738/1588555)

# Setting up your dev environment

## Install Atom and dependencies

Atom is a good open-source text editor that can be turned into a fully fledged Charming IDE. Following are instructions on how to do that on Ubuntu.

Install Atom

```bash
sudo add-apt-repository ppa:webupd8team/atom
sudo apt-get update
sudo apt-get install atom
```

Install the python package manager and the python packages we need.

```bash
# python package manager and dependencies
sudo apt install python-pip python3-pip python-setuptools python3-setuptools\
                 charm-tools juju-deployer

# Dependencies of Charms so linter can check them
sudo pip3 install charms.reactive netifaces amulet click Flask charmhelpers

# Properly display jinja2 templates
apm install atom-jinja2
```

## Show active Juju model in bash prompt

This one is very handy, it show the active Juju model and controller in the bash prompt. (Thanks James Beedy!)

```
[sojobo:mesebrec/merlijntest] merlijn@travers:~$
```

Instructions to setup:

```
cd ~
wget https://gist.githubusercontent.com/jamesbeedy/a5816a6ecd9f64e4bb96c8ba4a153ade/raw/14f255db3172519504e52d8a33ec81e995e8ef66/.juju_context.py
chmod u+x .juju_context.py
```

And add the following code at the end of `.bashrc`.

```
function show_juju_env {
  local currentEnv
  currentEnv=`~/.juju_context.py`
  printf "[\e[38;5;70m%s\e[0m] " "$currentEnv"
}

export PS1="\$(show_juju_env)${PS1}";

```

## Setup Python 2 and Python 3 linting

Pyton linting (code checking) for both python 2 and python 3. We need both `pylint` and `pep8`.

- **Pep8** is the official python style guide. We should adhere to this without question. pep8 linting is also checked by default by `bundletester` so we need to be compatible with this.
- **Pylint** is incredibly awesome and helps you write good, clean code. However, it can be a bit pedantic at times. You can disable specific warnings by writing `#pylint: disable=<code>` either at the top of your file or at the line you want to ignore.

Install linting packages.

```bash
sudo pip2 install pylint
sudo pip3 install pylint
sudo apt install pep8
apm install linter linter-pylint python-indent pep8
```

We also want pylint to search the charm's `lib` directory for python dependencies. Add the following string to the pylint path in the config of the linter-pylint Atom package: `%f/../lib`.

Setup automatic detection of python2/python3.

```bash
mkdir ~/bin
```

`nano ~/bin/pylint` and add:

```bash
#!/bin/bash
if [[ $(head -n 1 "${@: -1}") == *python3* ]]
then
  pylint3 --extension-pkg-whitelist=lxml,netifaces "$@"
else
  pylint2 --extension-pkg-whitelist=lxml,netifaces "$@"
fi
```

`nano ~/bin/pylint2` and add:

```python
#!/usr/bin/python2
# EASY-INSTALL-ENTRY-SCRIPT: 'pylint','console_scripts','pylint'
__requires__ = 'pylint'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('pylint', 'console_scripts', 'pylint')()
    )
```

`nano ~/bin/pylint3` and add:

```python
#!/usr/bin/python3
# EASY-INSTALL-ENTRY-SCRIPT: 'pylint','console_scripts','pylint'
__requires__ = 'pylint'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('pylint', 'console_scripts', 'pylint')()
    )
```

and finally: `chmod u+x ~/bin/pylint ~/bin/pylint2 ~/bin/pylint3`. Log out and log back in to save the changes.

Pylint is a bit to pedantic for us. The following config file tells pylint to ignore some warnings. `nano ~/.pylintrc` and add the following.

```
[MASTER]

# Use multiple processes to speed up Pylint.
jobs=2

# Allow loading of arbitrary C extensions. Extensions are imported into the
# active Python interpreter and may run arbitrary code.
unsafe-load-any-extension=no

# A comma-separated list of package or module names from where C extensions may
# be loaded. Extensions are loading into the active Python interpreter and may
# run arbitrary code
extension-pkg-whitelist=lxml,netifaces,pygments


[MESSAGES CONTROL]

# Enable the message, report, category or checker with the given id(s). You can
# either give multiple identifier separated by comma (,) or put this option
# multiple time (only on the command line, not in the configuration file where
# it should appear only once). See also the "--disable" option for examples.
#enable=

# Disable the message, report, category or checker with the given id(s). You
# can either give multiple identifiers separated by comma (,) or put this
# option multiple times (only on the command line, not in the configuration
# file where it should appear only once).You can also use "--disable=all" to
# disable everything first and then reenable specific checks. For example, if
# you want to run only the similarities checker, you can use "--disable=all
# --enable=similarities". If you want to run only the classes checker, but have
# no Warning level messages displayed, use"--disable=all --enable=classes
# --disable=W"
disable=c0103,c0111,import-star-module-level,old-octal-literal,oct-method,print-statement,unpacking-in-except,parameter-unpacking,backtick,old-raise-syntax,old-ne-operator,long-suffix,dict-view-method,dict-iter-method,metaclass-assignment,next-method-called,raising-string,indexing-exception,raw_input-builtin,long-builtin,file-builtin,execfile-builtin,coerce-builtin,cmp-builtin,buffer-builtin,basestring-builtin,apply-builtin,filter-builtin-not-iterating,using-cmp-argument,useless-suppression,range-builtin-not-iterating,suppressed-message,no-absolute-import,old-division,cmp-method,reload-builtin,zip-builtin-not-iterating,intern-builtin,unichr-builtin,reduce-builtin,standarderror-builtin,unicode-builtin,xrange-builtin,coerce-method,delslice-method,getslice-method,setslice-method,input-builtin,round-builtin,hex-method,nonzero-method,map-builtin-not-iterating
```

# Handy commands and tips

When running `juju debug-hooks`, you enter a tmux session. The default tmux bindings on Ubuntu are a bit strange. ctrl-a is the default command. To enable sane mouse scrolling set `set-window-option -g mode-mouse on` in `~/.tmux.conf` of the server.

Debug reactive framework

```bash
charms.reactive -p get_states
```

pull PR from github

```bash
git pull origin pull/$PR_NUM/head
```

add submodule as directory

```bash
git submodule add <git@github ...> <dirname>
```

prettyprint json output

```bash
| python -m json.tool
```

grep and get text around match

```bash
cat log | grep -A10 <searchterm> # Next 10 lines
cat log | grep -B10 <searchterm> # Previous 10 lines
```

Debug IP traffic:

```bash
iptables -t mangle -I PREROUTING -p icmp --icmp-type 8 -j LOG --log-prefix "ICMP ON MANGLE: "
```

Mongo

```
show dbs
use db demo
show collections
coll = db['imec']
coll.find().skip(coll.count() - 20)
coll.find({"subscriptionId": { $exists : true }}).limit(1).sort({$natural:-1})
ObjectId("5714784653628548824c18de").getTimestamp()
```

Analyse disk space

```
tree -h --du /var | grep "G]"
sudo du -h /var | grep '[0-9\.]\+G'
```

reconnect to screen

```
    screen -r
```
