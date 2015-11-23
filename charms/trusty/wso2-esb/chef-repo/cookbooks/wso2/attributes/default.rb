#
# Author:: Thomas Vanhove (<thomas.vanhove@intec.ugent.be>)
# Cookbook Name:: WSO2
# Attributes:: default
#
# Copyright 2014, Ghent University - IBCN - iMinds
#
# All rights reserved
#

# Default ESB attributes
default['wso2esb']['install_dir'] = "/opt/wso2esb"
default['wso2esb']['log_dir'] = "/var/log/wso2esb"
default['wso2esb']['tmp_dir'] = "/app/wso2esb/tmp"
default['wso2esb']['user_dir'] = "/home/esbuser"

default['wso2esb']['version'] = "4.9.0"
default['wso2esb']['mirror_url'] = "http://dist.wso2.org/products/enterprise-service-bus"

# Default ActiveMQ attributes
default['activemq']['install_dir'] = "/opt/activemq"
default['activemq']['version'] = "5.9.0"
default['activemq']['mirror_url'] = "http://www.apache.org/dyn/closer.cgi?path=/activemq/apache-activemq"
