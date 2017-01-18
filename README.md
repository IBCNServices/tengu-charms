# This Repository

This repository contains all the Open Source Charms, Bundles, Interfaces and Layers of the [Tengu platform](https://tengu.io/). Git submodules are used to link to code that is not contained in this repository.

# Tengu

Tengu is a flexible and dynamic data platform that can adapt to your needs. Tengu makes it possible to quickly set up and test a number of different data technologies such as Hadoop, Spark, Storm and Kafka. Tengu gives users the ability to connect different data technologies in order to get a complete distributed data solution. Tengu makes it possible to integrate with existing data and automation infrastructure. Existing automation artifacts such as Chef cookbooks and Puppet scripts can be reused to ease the transition to and integration with Tengu.

Tengu enables a number of use-cases:

 - Tengu provides a sandbox that enables guided experimentation with data tools. **Companies that want to get started with big data technologies** can use Tengu to build and test different big data solutions to see what fits their use-case.
 - **Companies that want to integrate big data tools into their existing infrastructure** can use Tengu to manage the integration between big data tools and their existing data infrastructure. Because Tengu is automation-tool independent, it can easily reuse existing automation artifacts such as Chef cookbooks and Puppet scripts.
 - **Developers that want to accelerate adoption of their data tools** can capture the operational knowledge of their data tool in Tengu to allow fast and easy deployment and integration.

## Integrating a project into Tengu

When you integrate your data tool into Tengu, user can very easily integrate your tool in their workflows. By using [Juju](https://jujucharms.com/) at its core, Tengu enables you to connect your data tool to the wide range of tools already available in Tengu.

When you write a Juju Charm, you capture the best practice operational knowledge of your data tool and enable others to reuse this knowledge. The first step is to capture the knowledge of how to **install and configure** your data tool. This enables users to rapidly deploy and test your data tool. The second step is to capture the knowledge of the options for **communication and collaboration with other data tools**. When you implement existing interfaces in your Charm, **users can swap out existing data tools and replace them by your solution.** This enables very fast adoption of new data tools.

The Juju docs contain a good [high-level overview of what Juju is](https://jujucharms.com/docs/stable/about-juju). Are you planning to integrate you data tool and want some guidance? Don't hesitate to contact us! You can contact me at [merlijn.sebrechts@gmail.com](mailto:merlijn.sebrechts@gmail.com).

# Default Tengu license:

## Plain text

```
Copyright (C) 2016  Ghent University

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

```

## Hash comments

```
# Copyright (C) 2016  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

```
