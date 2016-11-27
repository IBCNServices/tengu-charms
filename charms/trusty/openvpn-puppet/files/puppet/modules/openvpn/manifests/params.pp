# === License
#
# Copyright 2013 Raffael Schmid, <raffael@yux.ch>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
class openvpn::params {

  case $::osfamily {
    'RedHat': {
      $etc_directory       = '/etc'
      $root_group          = 'root'
      $group               = 'nobody'
      $link_openssl_cnf    = true
      $pam_module_path     = '/usr/lib64/openvpn/plugin/lib/openvpn-auth-pam.so'
      $additional_packages = ['easy-rsa']
      $easyrsa_source      = '/usr/share/easy-rsa/2.0'
      $namespecific_rclink = false

      # Redhat/Centos >= 7.0
      if(versioncmp($::operatingsystemrelease, '7.0') >= 0) and $::operatingsystem != 'Amazon' {
        $systemd = true
      # Redhat/Centos < 7
      } else {
        $systemd = false
      }

      $ldap_auth_plugin_location = undef # no ldap plugin on redhat/centos
    }
    'Debian': { # Debian/Ubuntu
      $etc_directory       = '/etc'
      $root_group          = 'root'
      $group               = 'nogroup'
      $link_openssl_cnf    = true
      $pam_module_path     = '/usr/lib/openvpn/openvpn-auth-pam.so'
      $namespecific_rclink = false

      case $::operatingsystem {
        'Debian': {
          # Version > 8.0, jessie
          if(versioncmp($::operatingsystemrelease, '8.0') >= 0) {
            $additional_packages       = ['easy-rsa','openvpn-auth-ldap']
            $easyrsa_source            = '/usr/share/easy-rsa/'
            $ldap_auth_plugin_location = '/usr/lib/openvpn/openvpn-auth-ldap.so'
            $systemd                   = true

          # Version > 7.0, wheezy
          } elsif(versioncmp($::operatingsystemrelease, '7.0') >= 0) {
            $additional_packages       = ['openvpn-auth-ldap']
            $easyrsa_source            = '/usr/share/doc/openvpn/examples/easy-rsa/2.0'
            $ldap_auth_plugin_location = '/usr/lib/openvpn/openvpn-auth-ldap.so'
            $systemd                   = false
          } else {
            $additional_packages       = undef
            $easyrsa_source            = '/usr/share/doc/openvpn/examples/easy-rsa/2.0'
            $ldap_auth_plugin_location = undef
            $systemd                   = false
          }
        }
        'Ubuntu': {
          # Version > 15.04, vivid
          if(versioncmp($::operatingsystemrelease, '15.04') >= 0){
            $additional_packages       = ['easy-rsa','openvpn-auth-ldap']
            $easyrsa_source            = '/usr/share/easy-rsa/'
            $ldap_auth_plugin_location = '/usr/lib/openvpn/openvpn-auth-ldap.so'
            $systemd                   = true

          # Version > 13.10, saucy
          } elsif(versioncmp($::operatingsystemrelease, '13.10') >= 0) {
            $additional_packages       = ['easy-rsa','openvpn-auth-ldap']
            $easyrsa_source            = '/usr/share/easy-rsa/'
            $ldap_auth_plugin_location = '/usr/lib/openvpn/openvpn-auth-ldap.so'
            $systemd                   = false
          } else {
            $additional_packages       = undef
            $easyrsa_source            = '/usr/share/doc/openvpn/examples/easy-rsa/2.0'
            $ldap_auth_plugin_location = undef
            $systemd                   = false
          }
        }
        default: {
          fail("Unsupported OS/Distribution ${::osfamily}/${::operatingsystem}")
        }
      }
    }
    'Archlinux': {
      $etc_directory             = '/etc'
      $root_group                = 'root'
      $additional_packages       = ['easy-rsa']
      $easyrsa_source            = '/usr/share/easy-rsa/'
      $group                     = 'nobody'
      $ldap_auth_plugin_location = undef # unsupported
      $link_openssl_cnf          = true
      $systemd                   = true
      $namespecific_rclink       = false
    }
    'Linux': {
      case $::operatingsystem {
        'Amazon': {
          $etc_directory             = '/etc'
          $root_group                = 'root'
          $group                     = 'nobody'
          $additional_packages       = ['easy-rsa']
          $easyrsa_source            = '/usr/share/easy-rsa/2.0'
          $ldap_auth_plugin_location = undef
          $systemd                   = false
          $link_openssl_cnf          = true
          $pam_module_path           = '/usr/lib/openvpn/openvpn-auth-pam.so'
          $namespecific_rclink       = false
        }
        default: {
          fail("Unsupported OS/Distribution ${::osfamily}/${::operatingsystem}")
        }
      }
    }
    'FreeBSD': {
      $etc_directory       = '/usr/local/etc'
      $root_group          = 'wheel'
      $group               = 'nogroup'
      $link_openssl_cnf    = true
      $pam_module_path     = '/usr/local/lib/openvpn/openvpn-auth-pam.so'
      $additional_packages = ['easy-rsa']
      $easyrsa_source      = '/usr/local/share/easy-rsa'
      $namespecific_rclink = true
    }
    default: {
      fail("Not supported OS family ${::osfamily}")
    }
  }
}
