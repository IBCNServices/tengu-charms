#
# Author:: Thomas Vanhove (<thomas.vanhove@intec.ugent.be>)
# Cookbook Name:: wso2
# Recipe:: Enterprise Service Bus
#
# Copyright 2014, Ghent University - IBCN - iMinds
#
# All rights reserved
#

include_recipe "java"

# Install unzip
package "unzip" do
  action :install
end

# Setup wso2 group
group "wso2"

# Setup ESB user
user "esbuser" do
  comment "ESB user"
  gid "wso2"
  shell "/bin/bash"
  home "#{node['wso2esb']['user_dir']}"
  password "$1$nSsd.3DF$ZLozCLTFrQ7qgEQEo1rPN."
  supports :manage_home => true
end

directory node['wso2esb']['install_dir'] do
  group "wso2"
  user "esbuser"
  action :create
  recursive true
end

# Transfer ESB zip
cookbook_file "#{Chef::Config[:file_cache_path]}/wso2esb-#{node['wso2esb']['version']}.zip" do
  source "wso2esb-#{node['wso2esb']['version']}.zip"
  action :create_if_missing
  user "esbuser"
  group "wso2"
  mode 00744
end

# Unzip into installation directory
execute "unzip" do
  creates "#{node['wso2esb']['install_dir']}/wso2esb-#{node['wso2esb']['version']}"
  cwd "#{node['wso2esb']['install_dir']}"
  command "unzip #{Chef::Config[:file_cache_path]}/wso2esb-#{node['wso2esb']['version']}.zip -d #{node['wso2esb']['install_dir']}"
end

# Create a link from the specific version to a generic current folder
link "#{node['wso2esb']['install_dir']}/current" do
  to "#{node['wso2esb']['install_dir']}/wso2esb-#{node['wso2esb']['version']}"
end

# Change owner of ESB dir
execute "chown" do
  cwd "#{Chef::Config[:file_cache_path]}"
  command "sudo chown -R esbuser #{node['wso2esb']['install_dir']}"
end

# Copy upstart service template (will only work on Ubuntu < 15.04)
template "wso2.upstart.conf" do
  path "/etc/init/wso2-esb.conf"
end

# register wso2 as upstart service. For some reason chef defaults to sysV init on virtual wall servers
service "wso2-esb" do
  provider Chef::Provider::Service::Upstart
  supports :restart => true, :start => true, :stop => true
end

# Export JAVA_HOME
execute "set JAVA_HOME" do
  cwd "/etc/profile.d/"
  user "esbuser"
  group "wso2"
  command "./jdk.sh"
end

# Start ESB server as service
service "wso2-esb" do
  action :restart
end
