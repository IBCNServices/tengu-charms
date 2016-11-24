# Best practices for contributing to Tengu

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

### Change config non-destructively (don't use templates)

Instead of using templates that completely overwrite existing config files, change them inline. This has a few advantages:

1. **Multiple handlers, layers and users can change a config file.** As long as they don't change the same values, this won't be a problem. Some users want to tweak config files that are managed by a Charm manually. This isn't possible if you use templates.
2. **It's more robuust.** We don't have to update the template when a new version of the application has different default config values.

*A handy function for non-destructive editing of config files is the [`re_edit_in_place`](https://pythonhosted.org/jujubigdata/api/jujubigdata.utils.html?highlight=re_edit_in_place#jujubigdata.utils.re_edit_in_place) function of jujubigdata utils*

### Small rules

- No Linter errors and no `charm proof` errors
- Always use the `check_..` functions. If error exit code doesn't matter, catch the exception.
- Use `shell=True`.
- Use upstart on trusty and systemd on xenial to start and stop services.
