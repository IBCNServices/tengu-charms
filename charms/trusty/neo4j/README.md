# Overview

This is a charm layer that installs OpenJDK or Oracle JDK.

# Configuration

### install-type

  This determines which OpenJDK packages to install. Valid options are `jre`
  or `jdk`. The default is `jre`, which will install the Java Runtime
  Environment (JRE). Setting this to `jdk` will install the Java
  Development Kit (JDK), which includes the JRE.

  Switch between the JRE and full (JRE+JDK) with the following:

      juju set openjdk install-type=full


### java-major

  Major version of Java to install.  This defaults to `7`.


### java-flavor

  Flavor of Java to install. Valid options are `openjdk` and `oracle`. The default is `openjdk`. Please note that the combination of java-flavor `oracle` and install-type `jre` will install the optimized server version of Oracle JRE.


### Supported Java major/flavor combinations

 - OpenJDK/JRE 6,7
 - Oracle JDK/JRE 8
