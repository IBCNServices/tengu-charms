#!/usr/bin/env python

import grp
import pwd
import unittest

from charmhelpers.contrib import bigdata


class TestDistConfig(unittest.TestCase):
    """
    Test that the ``dist.yaml`` settings were applied properly, such as users, groups, and dirs.

    This is done as a remote test on the deployed unit rather than a regular
    test under ``tests/`` because filling in the ``dist.yaml`` requires Juju
    context (e.g., config).
    """
    @classmethod
    def setUpClass(cls):
        cls.hadoop = bigdata.handlers.apache.HadoopBase()

    def test_groups(self):
        for name in self.hadoop.groups:
            try:
                grp.getgrnam(name)
            except KeyError:
                self.fail('Group {} is missing'.format(name))

    def test_users(self):
        for username, details in self.hadoop.users.items():
            try:
                user = pwd.getpwnam(username)
            except KeyError:
                self.fail('User {} is missing'.format(username))
            for groupname in details['groups']:
                try:
                    group = grp.getgrnam(groupname)
                except KeyError:
                    self.fail('Group {} referenced by user {} does not exist'.format(
                        groupname, username))
                if group.gr_gid != user.pw_gid:
                    self.assertIn(username, group.gr_mem, 'User {} not in group {}'.format(
                        username, groupname))

    def test_dirs(self):
        for name, details in self.hadoop.managed_dirs.items():
            dirpath = details['path']
            self.assertTrue(dirpath.isdir(), 'Dir {} is missing'.format(name))
            stat = dirpath.stat()
            owner = pwd.getpwuid(stat.st_uid).pw_name
            group = grp.getgrgid(stat.st_gid).gr_name
            perms = stat.st_mode & ~0o40000
            self.assertEqual(owner, details.get('owner', 'root'),
                             'Dir {} ({}) has wrong owner: {}'.format(name, dirpath, owner))
            self.assertEqual(group, details.get('group', 'root'),
                             'Dir {} ({}) has wrong group: {}'.format(name, dirpath, group))
            self.assertEqual(perms, details.get('perms', 0o744),
                             'Dir {} ({}) has wrong perms: 0o{:o}'.format(name, dirpath, perms))


if __name__ == '__main__':
    unittest.main()
