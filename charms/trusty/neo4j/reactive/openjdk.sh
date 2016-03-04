#!/bin/bash
set -ex

source charms.reactive.sh

# Remove any previous mention of JAVA_HOME, then append the appropriate value
# based on the source of our /usr/bin/java symlink (if it exists).
function update_java_home() {
    sed -i -e '/JAVA_HOME/d' /etc/environment

    if [[ -L "/usr/bin/java" ]]; then
        java_home=$(readlink -f /usr/bin/java | sed "s:/bin/java::")
        echo "JAVA_HOME=${java_home}" >> /etc/environment
    fi
}

@when 'java.connected'
@when_not 'java.installed'
function install() {
    install_type=$(config-get 'install-type')
    java_major=$(config-get 'java-major')

    # Install jre or jdk+jre depending on config. Since this is the first time
    # we're installing (when_not java.installed), update-alternatives will be
    # handled by the deb.
    apt-get update -q
    status-set maintenance "Installing OpenJDK ${java_major} (${install_type})"
    if [[ ${install_type} == "full" ]]; then
      apt-get install -qqy openjdk-${java_major}-jre-headless openjdk-${java_major}-jdk
    else
      apt-get install -qqy openjdk-${java_major}-jre-headless
    fi
    update_java_home

    # Send relation data
    java_home=$(readlink -f /usr/bin/java | sed "s:/bin/java::")
    java_version=$(java -version 2>&1 | grep -i version | head -1 | awk -F '"' {'print $2'})
    relation_call --state=java.connected set_ready $java_home $java_version

    set_state 'java.installed'
    status-set active "OpenJDK ${java_major} (${install_type}) installed"
}

@when 'java.connected' 'java.installed'
function check_version() {
    install_type=$(config-get 'install-type')
    java_major=$(config-get 'java-major')
    java_major_installed=$(java -version 2>&1 | grep -i version | head -1 | awk -F '.' {'print $2'})

    # Install new major version if the user has set 'java-major' to something
    # different than the version we have installed.
    if [[ $java_major != $java_major_installed ]]; then
        status-set maintenance "Installing OpenJDK ${java_major} (${install_type})"
        apt-get update -q
        if [[ ${install_type} == "full" ]]; then
          apt-get install -qqy openjdk-${java_major}-jre-headless openjdk-${java_major}-jdk
        else
          apt-get install -qqy openjdk-${java_major}-jre-headless
        fi
        status-set active "OpenJDK ${java_major} (${install_type}) installed"
        relation_call --state=java.connected set_ready $java_home $java_version
    elif [[ ${install_type} == 'jre' ]]; then
      # Remove the JDK if it exists but config tells us we only want the JRE
      if dpkg -s openjdk-${java_major}-jdk &> /dev/null; then
        status-set maintenance "Uninstalling OpenJDK ${java_major} (JDK)"
        apt-get remove --purge -qqy openjdk-${java_major}-jdk
      fi
    elif [[ ${install_type} == 'full' ]]; then
      # Install the JDK if config tells us we want a full install (it doesn't
      # hurt to install a package that is already installed. NOTE: this will
      # update any existing jdk package to the latest point release).
      status-set maintenance "Installing OpenJDK ${java_major} (${install_type})"
      apt-get install -qqy openjdk-${java_major}-jdk
    fi

    # Unconditionally switch all java-related symlinks to our major version.
    # This doesn't hurt anything even if we didn't make any package changes.
    # It helps ensure our system symlinks are always right, especially if we
    # changed major version or install type.
    java_alternative=$(update-java-alternatives -l | grep java-1.${java_major} | awk {'print $1'})
    update-java-alternatives -s ${java_alternative}
    update_java_home
    status-set active "OpenJDK ${java_major} (${install_type}) installed"
}

@when 'java.installed'
@when_not 'java.connected'
function uninstall() {
    # Uninstall all versions of OpenJDK
    status-set maintenance "Uninstalling OpenJDK (all versions)"
    apt-get remove --purge -qqy openjdk-[0-9]?-j.*
    update_java_home

    remove_state 'java.installed'
    status-set blocked "OpenJDK (all versions) uninstalled"
}

reactive_handler_main
